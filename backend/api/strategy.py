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
from simulation.sim_tags import build_sim_tag_batches, _call_sim_tag_batch
from simulation.game_engine import run_simulation

router = APIRouter(prefix="/decks", tags=["strategy"])

_executor = ThreadPoolExecutor(max_workers=12)


@router.post("/{deck_id}/strategy", response_model=dict)
async def generate_deck_strategy(
    deck_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generate a strategic profile with fully parallelized AI calls.
    """
    deck = db.query(Deck).filter(Deck.id == deck_id).first()
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")
    if deck.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your deck")

    cards = db.query(DeckCard).filter(DeckCard.deck_id == deck.id).all()
    if not cards:
        raise HTTPException(status_code=400, detail="Deck has no cards")

    total_start = time.time()
    loop = asyncio.get_event_loop()

    # Step 1: Analytics only - Scryfall fetch (fast, ~2s)
    t = time.time()
    analytics = await compute_analytics(cards, include_card_data=True)
    card_lookup = analytics.pop("_card_lookup", {})
    deck_info = {
        "name": deck.name,
        "format": deck.format,
        "description": deck.description,
        "preferences": deck.preferences,
    }
    print(f"TIMING: analytics (Scryfall) = {time.time() - t:.1f}s")

    # Step 2: PARALLEL PHASE 1 - role classification + base profile + sim tag batches
    # These are independent of each other
    t = time.time()

    role_future = loop.run_in_executor(
        _executor,
        lambda: classify_deck_roles(cards, card_lookup, deck_info)
    )

    profile_future = loop.run_in_executor(
        _executor,
        lambda: generate_base_profile(
            deck_info=deck_info, deck_cards=cards, card_lookup=card_lookup,
            analytics=analytics,
            role_data={"primary_creature_type": "None", "role_distribution": {}, "card_roles": []},
        )
    )

    # Prep sim tag batches (no AI, instant)
    sim_tag_batches = build_sim_tag_batches(cards, card_lookup)

    # Launch sim tag batches immediately - they don't depend on profile or roles
    sim_tag_futures = []
    for system_prompt, user_msg, batch in sim_tag_batches:
        future = loop.run_in_executor(
            _executor,
            lambda s=system_prompt, u=user_msg, b=batch: _call_sim_tag_batch(s, u, b)
        )
        sim_tag_futures.append(future)

    # Wait for roles + profile (needed before impact batches)
    role_data, profile = await asyncio.gather(role_future, profile_future)
    print(f"TIMING: phase 1 (roles + profile + sim tags started) = {time.time() - t:.1f}s")

    if "error" in profile:
        raise HTTPException(status_code=502, detail=f"Strategy generation failed: {profile['error']}")

    # Step 3: PARALLEL PHASE 2 - impact batches (need profile) + wait for sim tags
    t = time.time()
    impact_batches = build_impact_batches(
        deck_info=deck_info, deck_cards=cards, card_lookup=card_lookup,
        analytics=analytics, role_data=role_data, profile=profile,
    )
    print(f"TIMING: {len(impact_batches)} impact + {len(sim_tag_batches)} sim tag batches")

    # Launch impact batches
    impact_futures = []
    for system_prompt, user_msg in impact_batches:
        future = loop.run_in_executor(
            _executor,
            lambda s=system_prompt, u=user_msg: _call_impact_batch(s, u)
        )
        impact_futures.append(future)

    # Wait for ALL remaining tasks (impact batches + sim tag batches still running)
    all_remaining = impact_futures + sim_tag_futures
    completed = await asyncio.gather(*all_remaining, return_exceptions=True)
    print(f"TIMING: phase 2 (impact + sim tags) = {time.time() - t:.1f}s")

    # Split results
    impact_results = completed[:len(impact_futures)]
    sim_tag_results = completed[len(impact_futures):]

    # Merge impact ratings
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

    # Merge sim tags
    sim_tags = {}
    for batch_result in sim_tag_results:
        if batch_result and isinstance(batch_result, dict):
            sim_tags.update(batch_result)
    profile["sim_tags"] = sim_tags

    # Step 4: Compact summary (instant)
    commander_text = _get_commander_text(cards, card_lookup)
    profile["deck_summary"] = _build_compact_summary(
        deck_info=deck_info, analytics=analytics, role_data=role_data,
        profile=profile, commander_text=commander_text,
    )

    # Step 5: Simulation + color health (fast, ~1-3s)
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

    # Save strategy profile
    deck.strategy_profile = profile

    # Write per-card AI context to deck_cards
    impact_lookup = {}
    for rating in deduped:
        impact_lookup[rating.get("card_name", "").lower()] = rating

    role_lookup = {}
    for cr in role_data.get("card_roles", []):
        role_lookup[cr["name"].lower()] = cr

    for card in cards:
        card_name_lower = card.card_name.lower()
        impact = impact_lookup.get(card_name_lower, {})
        role_info = role_lookup.get(card_name_lower, {})

        card.ai_context = {
            "role": role_info.get("primary_role", "unknown"),
            "secondary_roles": role_info.get("secondary_roles", []),
            "impact_score": impact.get("score", None),
            "impact_reason": impact.get("reason", None),
            "synergy_notes": role_info.get("synergy_notes", ""),
            "is_critical": card.card_name in profile.get("critical_cards", []),
        }

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
    """Get the stored strategic profile for a deck."""
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