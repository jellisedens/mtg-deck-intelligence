"""
Deck Wizard - auto-generates a starter shell for new Commander decks.

Modes:
- starter: ~25 top EDHREC spells + 37 lands (quick start, room to customize)
- average: complete EDHREC average deck (what most players actually run)
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
from services.edhrec import fetch_commander_profile, fetch_average_deck
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
    - average: complete EDHREC average deck (what most players actually run)
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

    # ── Average Mode: fetch complete EDHREC average deck ─────
    if mode == "average":
        avg_deck = await fetch_average_deck(commander.card_name)
        if not avg_deck:
            raise HTTPException(status_code=502, detail="Failed to fetch EDHREC average deck for this commander")

        added_cards = []

        # Batch resolve non-land cards via Scryfall collection
        non_basic_cards = avg_deck["cards"]
        identifiers = [{"id": c["scryfall_id"]} for c in non_basic_cards if c["scryfall_id"]]
        name_only = [c for c in non_basic_cards if not c["scryfall_id"]]
        identifiers.extend([{"name": c["name"]} for c in name_only])

        resolved = await scryfall_service.get_collection(identifiers)
        if "data" in resolved:
            for card_data in resolved["data"]:
                name = card_data.get("name", "")
                if name.lower() in existing_names or name.lower() == commander.card_name.lower():
                    continue
                card = DeckCard(
                    deck_id=deck.id,
                    scryfall_id=card_data["id"],
                    card_name=name,
                    quantity=1,
                    board="main",
                )
                db.add(card)
                added_cards.append({
                    "card_name": name,
                    "scryfall_id": card_data["id"],
                    "type": card_data.get("type_line", ""),
                    "source": "edhrec_average",
                })
                existing_names.add(name.lower())

        # Add basic lands
        for basic_name, qty in avg_deck.get("basics", {}).items():
            try:
                card_data = await scryfall_service.get_card_by_name(basic_name)
                if "error" not in card_data:
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
                        "type": "Basic Land",
                        "quantity": qty,
                        "source": "edhrec_average",
                    })
            except Exception as e:
                print(f"[Wizard] Failed to resolve basic {basic_name}: {e}")

        # Save color identity and cache profile
        profile = deck.strategy_profile or {}
        profile["color_identity"] = avg_deck.get("color_identity", [])
        deck.strategy_profile = profile

        prefs = deck.preferences or {}
        prefs["color_identity"] = avg_deck.get("color_identity", [])
        deck.preferences = prefs

        db.commit()

        total_added = sum(c.get("quantity", 1) for c in added_cards)
        return {
            "status": "ok",
            "mode": "average",
            "commander": commander.card_name,
            "color_identity": avg_deck.get("color_identity", []),
            "cards_added": total_added,
            "total_deck_size": existing_count + total_added,
            "edhrec_decks_analyzed": avg_deck.get("total_decks", 0),
            "cards": added_cards,
        }

    # ── Starter Mode: EDHREC average deck lands only ─────────
    avg_deck = await fetch_average_deck(commander.card_name)

    added_cards = []
    color_identity = []

    if avg_deck:
        color_identity = avg_deck.get("color_identity", [])

        # Extract only land cards from the average deck
        land_cards = [c for c in avg_deck["cards"] if c.get("category") == "lands"]
        if land_cards:
            identifiers = [{"id": c["scryfall_id"]} for c in land_cards if c["scryfall_id"]]
            identifiers.extend([{"name": c["name"]} for c in land_cards if not c["scryfall_id"]])

            resolved = await scryfall_service.get_collection(identifiers)
            if "data" in resolved:
                for card_data in resolved["data"]:
                    name = card_data.get("name", "")
                    if name.lower() in existing_names:
                        continue
                    card = DeckCard(
                        deck_id=deck.id,
                        scryfall_id=card_data["id"],
                        card_name=name,
                        quantity=1,
                        board="main",
                    )
                    db.add(card)
                    added_cards.append({
                        "card_name": name,
                        "scryfall_id": card_data["id"],
                        "type": card_data.get("type_line", ""),
                        "source": "edhrec_average_lands",
                    })
                    existing_names.add(name.lower())

        # Add basic lands
        for basic_name, qty in avg_deck.get("basics", {}).items():
            try:
                card_data = await scryfall_service.get_card_by_name(basic_name)
                if "error" not in card_data:
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
                        "type": "Basic Land",
                        "quantity": qty,
                        "source": "edhrec_average_lands",
                    })
            except Exception as e:
                print(f"[Wizard] Failed to resolve basic {basic_name}: {e}")

    else:
        # Fallback: use generated mana base if EDHREC fails
        commander_data = await scryfall_service.get_card_by_name(commander.card_name)
        if "error" not in commander_data:
            color_identity = commander_data.get("color_identity", [])

        land_names = _build_mana_base(color_identity, total_lands=37)
        basic_names = set(BASIC_LAND_MAP.values()) | {"Wastes"}
        land_counts = {}
        for land in land_names:
            if land.lower() in existing_names and land not in basic_names:
                continue
            land_counts[land] = land_counts.get(land, 0) + 1

        for land_name, qty in land_counts.items():
            try:
                card_data = await scryfall_service.get_card_by_name(land_name)
                if "error" in card_data:
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
                    "source": "generated_mana_base",
                })
            except Exception as e:
                print(f"[Wizard] Failed to resolve land {land_name}: {e}")

    # Save color identity
    profile = deck.strategy_profile or {}
    profile["color_identity"] = color_identity
    deck.strategy_profile = profile

    prefs = deck.preferences or {}
    prefs["color_identity"] = color_identity
    deck.preferences = prefs

    db.commit()

    total_added = sum(c.get("quantity", 1) for c in added_cards)
    return {
        "status": "ok",
        "mode": "starter",
        "commander": commander.card_name,
        "color_identity": color_identity,
        "cards_added": total_added,
        "total_deck_size": existing_count + total_added,
        "edhrec_decks_analyzed": avg_deck.get("total_decks", 0) if avg_deck else 0,
        "cards": added_cards,
    }