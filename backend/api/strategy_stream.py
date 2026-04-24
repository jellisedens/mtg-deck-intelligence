"""
Server-Sent Events endpoint for strategy generation with progress updates.
"""

from uuid import UUID
import asyncio
import time
import json
from concurrent.futures import ThreadPoolExecutor
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
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


def _sse_message(data: dict) -> str:
    """Format a dict as an SSE message."""
    return f"data: {json.dumps(data)}\n\n"


@router.get("/{deck_id}/strategy/stream")
async def stream_strategy_generation(
    deck_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generate strategy profile with real-time progress updates via SSE.
    Connect with EventSource in the frontend to receive progress.
    """
    deck = db.query(Deck).filter(Deck.id == deck_id).first()
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")
    if deck.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your deck")

    cards = db.query(DeckCard).filter(DeckCard.deck_id == deck.id).all()
    if not cards:
        raise HTTPException(status_code=400, detail="Deck has no cards")

    async def generate():
        total_start = time.time()
        loop = asyncio.get_event_loop()

        # Step 1: Analytics
        yield _sse_message({
            "step": "analytics",
            "message": "Analyzing deck composition...",
            "progress": 5,
        })

        analytics = await compute_analytics(cards, include_card_data=True)
        card_lookup = analytics.pop("_card_lookup", {})
        deck_info = {"name": deck.name, "format": deck.format, "description": deck.description}

        yield _sse_message({
            "step": "analytics",
            "message": "Deck data loaded",
            "progress": 10,
        })

        # Step 2: Phase 1 - roles + profile + sim tags (parallel)
        yield _sse_message({
            "step": "phase1",
            "message": "Classifying card roles and generating strategy...",
            "progress": 15,
        })

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

        sim_tag_batches = build_sim_tag_batches(cards, card_lookup)
        sim_tag_futures = []
        for system_prompt, user_msg, batch in sim_tag_batches:
            future = loop.run_in_executor(
                _executor,
                lambda s=system_prompt, u=user_msg, b=batch: _call_sim_tag_batch(s, u, b)
            )
            sim_tag_futures.append(future)

        # Track completion of phase 1 tasks
        sim_tags_done = 0
        total_sim_batches = len(sim_tag_futures)

        # Wait for roles and profile first
        role_data = await role_future
        yield _sse_message({
            "step": "roles",
            "message": "Card roles classified",
            "progress": 30,
        })

        profile = await profile_future
        yield _sse_message({
            "step": "profile",
            "message": "Strategy profile generated",
            "progress": 40,
        })

        if "error" in profile:
            yield _sse_message({
                "step": "error",
                "message": f"Strategy generation failed: {profile['error']}",
                "progress": 0,
            })
            return

        # Step 3: Launch impact batches
        yield _sse_message({
            "step": "impact",
            "message": "Rating card impact scores...",
            "progress": 45,
        })

        impact_batches = build_impact_batches(
            deck_info=deck_info, deck_cards=cards, card_lookup=card_lookup,
            analytics=analytics, role_data=role_data, profile=profile,
        )

        impact_futures = []
        for system_prompt, user_msg in impact_batches:
            future = loop.run_in_executor(
                _executor,
                lambda s=system_prompt, u=user_msg: _call_impact_batch(s, u)
            )
            impact_futures.append(future)

        # Wait for all remaining tasks
        all_remaining = impact_futures + sim_tag_futures
        total_remaining = len(all_remaining)
        done_count = 0

        for coro in asyncio.as_completed(all_remaining):
            await coro
            done_count += 1
            pct = 45 + int((done_count / total_remaining) * 40)
            yield _sse_message({
                "step": "batches",
                "message": f"Processing AI batches ({done_count}/{total_remaining})...",
                "progress": pct,
            })

        # Collect results
        impact_results = [f.result() for f in impact_futures]
        sim_tag_results = [f.result() for f in sim_tag_futures]

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

        yield _sse_message({
            "step": "summary",
            "message": "Building deck summary...",
            "progress": 88,
        })

        # Compact summary
        commander_text = _get_commander_text(cards, card_lookup)
        profile["deck_summary"] = _build_compact_summary(
            deck_info=deck_info, analytics=analytics, role_data=role_data,
            profile=profile, commander_text=commander_text,
        )

        # Step 4: Simulation
        yield _sse_message({
            "step": "simulation",
            "message": "Running 500-game simulation...",
            "progress": 90,
        })

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

        yield _sse_message({
            "step": "saving",
            "message": "Saving profile to database...",
            "progress": 95,
        })

        # Role data
        profile["role_data"] = {
            "role_distribution": role_data.get("role_distribution", {}),
            "card_roles": role_data.get("card_roles", []),
            "primary_creature_type": role_data.get("primary_creature_type"),
        }

        # Save
        deck.strategy_profile = profile
        db.commit()

        elapsed = round(time.time() - total_start, 1)

        yield _sse_message({
            "step": "complete",
            "message": f"Strategy profile complete! ({elapsed}s)",
            "progress": 100,
            "stats": {
                "sim_tags_generated": len(sim_tags),
                "roles_classified": len(role_data.get("card_roles", [])),
                "impact_ratings": len(deduped),
                "simulation_games": sim_results.get("games_simulated", 0),
                "elapsed_seconds": elapsed,
            }
        })

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )