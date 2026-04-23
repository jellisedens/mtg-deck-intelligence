from uuid import UUID
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.session import get_db
from models.user import User
from models.deck import Deck
from models.deck_card import DeckCard
from api.deps import get_current_user
from services.analytics import compute_analytics
from services.role_classifier import classify_deck_roles
from services.strategy_profiler import (
    generate_base_profile,
    build_impact_batches,
    _call_impact_batch,
    _build_compact_summary,
    _get_commander_text,
)
from services.mana_analyzer import compute_color_health
from simulation.sim_tags import generate_sim_tags
from simulation.game_engine import run_simulation

router = APIRouter(prefix="/decks", tags=["strategy"])

_executor = ThreadPoolExecutor(max_workers=10)


@router.post("/{deck_id}/strategy", response_model=dict)
async def generate_deck_strategy(
    deck_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    deck = db.query(Deck).filter(Deck.id == deck_id).first()
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")
    if deck.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your deck")

    cards = db.query(DeckCard).filter(DeckCard.deck_id == deck.id).all()
    if not cards:
        raise HTTPException(status_code=400, detail="Deck has no cards")

    total_start = time.time()

    # Step 1: Analytics + roles (no AI)
    t = time.time()
    analytics = await compute_analytics(cards, include_card_data=True)
    card_lookup = analytics.pop("_card_lookup", {})
    deck_info = {"name": deck.name, "format": deck.format, "description": deck.description}
    role_data = classify_deck_roles(cards, card_lookup, deck_info)
    print(f"TIMING: analytics + roles = {time.time() - t:.1f}s")

    # Step 2: Base profile (1 AI call)
    t = time.time()
    loop = asyncio.get_event_loop()
    profile = await loop.run_in_executor(
        _executor,
        lambda: generate_base_profile(
            deck_info=deck_info, deck_cards=cards, card_lookup=card_lookup,
            analytics=analytics, role_data=role_data,
        )
    )
    print(f"TIMING: base profile = {time.time() - t:.1f}s")

    if "error" in profile:
        raise HTTPException(status_code=502, detail=f"Strategy generation failed: {profile['error']}")

    # Step 3: Prep impact batches (no AI)
    impact_batches = build_impact_batches(
        deck_info=deck_info, deck_cards=cards, card_lookup=card_lookup,
        analytics=analytics, role_data=role_data, profile=profile,
    )
    print(f"TIMING: {len(impact_batches)} impact batches prepared")

    # Step 4: PARALLEL - impact batches + sim tags
    t = time.time()
    all_futures = []

    for system_prompt, user_msg in impact_batches:
        future = loop.run_in_executor(
            _executor,
            lambda s=system_prompt, u=user_msg: _call_impact_batch(s, u)
        )
        all_futures.append(future)

    sim_tags_future = loop.run_in_executor(
        _executor,
        lambda: generate_sim_tags(cards, card_lookup)
    )
    all_futures.append(sim_tags_future)

    # Wait for ALL to complete
    all_results = await asyncio.gather(*all_futures)
    print(f"TIMING: parallel section ({len(all_futures)} tasks) = {time.time() - t:.1f}s")

    # Split results - impact batches are first, sim tags is last
    impact_results = all_results[:-1]
    sim_tags = all_results[-1]

    # Merge and deduplicate impact ratings
    all_ratings = []
    for batch_result in impact_results:
        if batch_result and isinstance(batch_result, list):
            all_ratings.extend(batch_result)

    seen = set()
    deduped = []
    for rating in all_ratings:
        name = rating.get("card_name", "").lower()
        if name not in seen:
            seen.add(name)
            deduped.append(rating)

    profile["card_impact_ratings"] = deduped
    profile["sim_tags"] = sim_tags

    # Step 5: Compact summary
    commander_text = _get_commander_text(cards, card_lookup)
    profile["deck_summary"] = _build_compact_summary(
        deck_info=deck_info, analytics=analytics, role_data=role_data,
        profile=profile, commander_text=commander_text,
    )

    # Step 6: Simulation + color health
    t = time.time()
    main_deck_cards = []
    for card in cards:
        if card.board != "main":
            continue
        card_data = card_lookup.get(card.scryfall_id)
        if card_data:
            main_deck_cards.append({"card_data": card_data, "quantity": card.quantity})

    sim_results = {}
    if main_deck_cards:
        sim_results = run_simulation(
            deck_cards=main_deck_cards, sim_tags=sim_tags, n_games=500, turns=10,
        )
        profile["cached_simulation"] = sim_results
        color_health = compute_color_health(sim_results, analytics)
        profile["color_health"] = color_health
    print(f"TIMING: simulation + color health = {time.time() - t:.1f}s")

    # Role data
    profile["role_data"] = {
        "role_distribution": role_data.get("role_distribution", {}),
        "card_roles": role_data.get("card_roles", []),
        "primary_creature_type": role_data.get("primary_creature_type"),
    }

    # Save
    deck.strategy_profile = profile
    db.commit()
    db.refresh(deck)

    print(f"TIMING: TOTAL = {time.time() - total_start:.1f}s")

    response = {k: v for k, v in profile.items() if k not in ("sim_tags", "cached_simulation")}
    response["sim_tags_generated"] = len(sim_tags)
    response["roles_classified"] = len(role_data.get("card_roles", []))
    response["simulation_games"] = sim_results.get("games_simulated", 0) if main_deck_cards else 0

    return response


@router.get("/{deck_id}/strategy", response_model=dict)
async def get_deck_strategy(
    deck_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    deck = db.query(Deck).filter(Deck.id == deck_id).first()
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")
    if deck.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your deck")

    if not deck.strategy_profile:
        raise HTTPException(status_code=404, detail="No strategy profile generated yet.")

    profile = deck.strategy_profile
    response = {k: v for k, v in profile.items() if k not in ("sim_tags", "cached_simulation")}
    return response