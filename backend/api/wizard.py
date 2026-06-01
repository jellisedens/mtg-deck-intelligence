"""
Deck Wizard - auto-generates a starter shell for new Commander decks.

Modes:
- starter: ~25 top EDHREC spells + 37 lands (quick start, room to customize)
- average: ~62 EDHREC spells + 37 lands (full average community deck)
"""

import asyncio
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from database.session import get_db
from models.user import User
from models.deck import Deck
from models.deck_card import DeckCard
from api.deps import get_current_user
from services.edhrec import fetch_commander_profile
from services.scryfall import scryfall_service

router = APIRouter(prefix="/decks", tags=["wizard"])

BASIC_LAND_MAP = {
    "W": "Plains",
    "U": "Island",
    "B": "Swamp",
    "R": "Mountain",
    "G": "Forest",
}

DUAL_LANDS = {
    "WU": ["Azorius Guildgate", "Tranquil Cove"],
    "WB": ["Orzhov Guildgate", "Scoured Barrens"],
    "WR": ["Boros Guildgate", "Wind-Scarred Crag"],
    "WG": ["Selesnya Guildgate", "Blossoming Sands"],
    "UB": ["Dimir Guildgate", "Dismal Backwater"],
    "UR": ["Izzet Guildgate", "Swiftwater Cliffs"],
    "UG": ["Simic Guildgate", "Thornwood Falls"],
    "BR": ["Rakdos Guildgate", "Bloodfell Caves"],
    "BG": ["Golgari Guildgate", "Jungle Hollow"],
    "RG": ["Gruul Guildgate", "Rugged Highlands"],
}

COLORLESS_UTILITY_LANDS = [
    "Command Tower",
    "Exotic Orchard",
    "Path of Ancestry",
]


class GenerateShellRequest(BaseModel):
    mode: str = "starter"  # "starter" or "average"


def _build_mana_base(color_identity, total_lands=37):
    """Generate a balanced mana base for a Commander deck."""
    colors = [c for c in "WUBRG" if c in color_identity]
    lands = []

    if not colors:
        lands.append("Command Tower")
        lands.append("Reliquary Tower")
        lands.append("Rogue's Passage")
        remaining = total_lands - len(lands)
        for _ in range(remaining):
            lands.append("Wastes")
        return lands

    lands.extend(COLORLESS_UTILITY_LANDS[:min(3, total_lands)])

    if len(colors) >= 2:
        for i in range(len(colors)):
            for j in range(i + 1, len(colors)):
                pair = colors[i] + colors[j]
                pair_lands = DUAL_LANDS.get(pair, [])
                for land in pair_lands[:1]:
                    if len(lands) < total_lands:
                        lands.append(land)

    remaining = total_lands - len(lands)
    if remaining > 0:
        basics_per_color = remaining // len(colors)
        extras = remaining % len(colors)
        for i, color in enumerate(colors):
            count = basics_per_color + (1 if i < extras else 0)
            basic_name = BASIC_LAND_MAP[color]
            for _ in range(count):
                lands.append(basic_name)

    return lands


def _select_edhrec_cards(profile, color_identity, max_cards=28):
    """Select the best cards from EDHREC data for a starter shell."""
    cards = profile.get("cards", [])
    non_land_cards = [
        c for c in cards
        if c.get("category") not in ("land", "utility_land")
    ]
    for card in non_land_cards:
        card["_score"] = card["inclusion_pct"] + (card.get("synergy", 0) * 100)
    non_land_cards.sort(key=lambda c: c["_score"], reverse=True)
    selected = non_land_cards[:max_cards]
    for card in selected:
        card.pop("_score", None)
    return selected


def _select_edhrec_lands(profile, existing_names, max_lands=10):
    """Select popular utility lands from EDHREC data."""
    cards = profile.get("cards", [])
    land_cards = [
        c for c in cards
        if c.get("category") in ("land", "utility_land")
        and c["name"].lower() not in existing_names
        and c["inclusion_pct"] >= 15
    ]
    land_cards.sort(key=lambda c: c["inclusion_pct"], reverse=True)
    return land_cards[:max_lands]


@router.post("/{deck_id}/wizard/generate-shell")
async def generate_deck_shell(
    deck_id: UUID,
    request: GenerateShellRequest = GenerateShellRequest(),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Auto-generate a starter shell for a Commander deck.

    Modes:
    - starter: ~25 EDHREC spells + 37 basic lands (quick start)
    - average: ~62 EDHREC spells + 37 lands including EDHREC utility lands (full average deck)
    """
    deck = db.query(Deck).filter(Deck.id == deck_id).first()
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")
    if deck.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your deck")
    if deck.format != "commander":
        raise HTTPException(status_code=400, detail="Shell generation is only for Commander")

    mode = request.mode
    if mode not in ("starter", "average"):
        raise HTTPException(status_code=400, detail="Mode must be 'starter' or 'average'")

    commander = db.query(DeckCard).filter(
        DeckCard.deck_id == deck.id,
        DeckCard.board == "commander",
    ).first()
    if not commander:
        raise HTTPException(status_code=400, detail="No commander set")

    existing_cards = db.query(DeckCard).filter(DeckCard.deck_id == deck.id).all()
    existing_names = {c.card_name.lower() for c in existing_cards}
    existing_count = sum(c.quantity for c in existing_cards)

    slots_available = 100 - existing_count
    if slots_available <= 0:
        raise HTTPException(status_code=400, detail="Deck is already at 100 cards")

    commander_data = await scryfall_service.get_card_by_name(commander.card_name)
    if "error" in commander_data:
        raise HTTPException(status_code=502, detail="Failed to fetch commander data")

    color_identity = commander_data.get("color_identity", [])
    budget = (deck.preferences or {}).get("budget")

    edhrec_profile = await fetch_commander_profile(commander.card_name)

    added_cards = []
    cards_to_add = []

    # Auto-includes
    auto_includes = ["Sol Ring"]
    for card_name in auto_includes:
        if card_name.lower() not in existing_names:
            cards_to_add.append(card_name)
            existing_names.add(card_name.lower())

    # Determine how many spells to pull based on mode
    land_slots = 37
    if mode == "average":
        # Fill as much as possible: 99 - 1 commander - 37 lands = 61 spell slots
        spell_slots = min(slots_available - land_slots - len(cards_to_add), 62)
        spell_slots = max(spell_slots, 15)
    else:
        # Starter: ~25 spells, leave room for user customization
        spell_slots = min(slots_available - land_slots - len(cards_to_add), 25)
        spell_slots = max(spell_slots, 15)

    # EDHREC staples
    if edhrec_profile:
        edhrec_picks = _select_edhrec_cards(
            edhrec_profile, color_identity,
            max_cards=spell_slots,
        )
        for pick in edhrec_picks:
            if pick["name"].lower() not in existing_names:
                cards_to_add.append(pick["name"])
                existing_names.add(pick["name"].lower())
        print(f"[Wizard] Mode={mode}: selected {len(edhrec_picks)} EDHREC spells")

    # Mana base
    land_names = _build_mana_base(color_identity, total_lands=land_slots)
    basic_names = set(BASIC_LAND_MAP.values()) | {"Wastes"}
    land_counts = {}
    for land in land_names:
        if land.lower() in existing_names and land not in basic_names:
            continue
        land_counts[land] = land_counts.get(land, 0) + 1

    # In average mode, also pull EDHREC-recommended utility lands
    edhrec_lands_added = 0
    if mode == "average" and edhrec_profile:
        edhrec_lands = _select_edhrec_lands(edhrec_profile, existing_names, max_lands=8)
        # Replace some basics with EDHREC utility lands
        basics_to_remove = min(len(edhrec_lands), sum(v for k, v in land_counts.items() if k in basic_names) // 2)
        removed = 0
        for basic in list(basic_names):
            if removed >= basics_to_remove:
                break
            if basic in land_counts and land_counts[basic] > 2:
                can_remove = min(land_counts[basic] - 2, basics_to_remove - removed)
                land_counts[basic] -= can_remove
                removed += can_remove

        for eland in edhrec_lands[:basics_to_remove]:
            if eland["name"].lower() not in existing_names:
                land_counts[eland["name"]] = 1
                existing_names.add(eland["name"].lower())
                edhrec_lands_added += 1
        print(f"[Wizard] Added {edhrec_lands_added} EDHREC utility lands")

    # Resolve non-land cards via Scryfall
    total_resolved = 0
    for i in range(0, len(cards_to_add), 10):
        batch = cards_to_add[i:i + 10]
        for card_name in batch:
            try:
                card_data = await scryfall_service.get_card_by_name(card_name)
                if "error" in card_data:
                    continue
                card_ci = set(card_data.get("color_identity", []))
                deck_ci = set(color_identity)
                if not card_ci.issubset(deck_ci):
                    continue
                card = DeckCard(
                    deck_id=deck.id,
                    scryfall_id=card_data["id"],
                    card_name=card_data["name"],
                    quantity=1,
                    board="main",
                )
                db.add(card)
                added_cards.append({
                    "card_name": card_data["name"],
                    "scryfall_id": card_data["id"],
                    "type": "spell",
                    "source": "edhrec" if edhrec_profile else "auto",
                    "image_uri": card_data.get("image_uris", {}).get("small", ""),
                })
                total_resolved += 1
            except Exception as e:
                print(f"[Wizard] Failed to resolve {card_name}: {e}")
                continue

    # Resolve lands
    for land_name, qty in land_counts.items():
        try:
            card_data = await scryfall_service.get_card_by_name(land_name)
            if "error" in card_data:
                continue
            if land_name not in basic_names and land_name.lower() in existing_names:
                continue
            card = DeckCard(
                deck_id=deck.id,
                scryfall_id=card_data["id"],
                card_name=card_data["name"],
                quantity=qty,
                board="main",
            )
            db.add(card)
            added_cards.append({
                "card_name": card_data["name"],
                "scryfall_id": card_data["id"],
                "type": "land",
                "quantity": qty,
                "source": "mana_base",
                "image_uri": card_data.get("image_uris", {}).get("small", ""),
            })
            total_resolved += qty
        except Exception as e:
            print(f"[Wizard] Failed to resolve land {land_name}: {e}")
            continue

    if edhrec_profile:
        profile = deck.strategy_profile or {}
        profile["edhrec_profile"] = edhrec_profile
        deck.strategy_profile = profile

    db.commit()

    return {
        "status": "ok",
        "mode": mode,
        "commander": commander.card_name,
        "color_identity": color_identity,
        "cards_added": len(added_cards),
        "total_deck_size": existing_count + total_resolved,
        "edhrec_decks_analyzed": edhrec_profile["total_decks"] if edhrec_profile else 0,
        "cards": added_cards,
    }