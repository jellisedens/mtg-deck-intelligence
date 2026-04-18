"""
Deck analytics engine.
Fetches card data from Scryfall and computes deck statistics.
"""

import re
from collections import defaultdict
from services.scryfall import scryfall_service


# Mana symbol regex — matches {W}, {U}, {B}, {R}, {G}, {C}, and generic like {3}
MANA_SYMBOL_PATTERN = re.compile(r"\{([^}]+)\}")
COLORS = ["W", "U", "B", "R", "G"]
COLOR_NAMES = {"W": "White", "U": "Blue", "B": "Black", "R": "Red", "G": "Green"}

# Card type categories to look for in the type_line
TYPE_CATEGORIES = [
    "Creature",
    "Instant",
    "Sorcery",
    "Enchantment",
    "Artifact",
    "Planeswalker",
    "Land",
    "Battle",
]


async def compute_analytics(deck_cards: list, include_card_data: bool = False) -> dict:
    """
    Compute full analytics for a deck.

    Args:
        deck_cards: list of DeckCard ORM objects (from the database)
        include_card_data: if True, include full card data in response (for AI context)

    Returns:
        dict with all analytics data
    """
    if not deck_cards:
        return _empty_analytics()

    # --- Fetch full card data from Scryfall ---
    identifiers = [{"id": card.scryfall_id} for card in deck_cards]
    scryfall_data = await scryfall_service.get_collection(identifiers)

    if "error" in scryfall_data:
        return {"error": scryfall_data["error"], "details": scryfall_data.get("details")}

    # Build a lookup: scryfall_id → full card data
    card_lookup = {}
    for card_data in scryfall_data.get("data", []):
        card_lookup[card_data["id"]] = card_data

    # --- Build expanded card list (respecting quantities) ---
    expanded_cards = []
    not_found = []

    for deck_card in deck_cards:
        full_data = card_lookup.get(deck_card.scryfall_id)
        if full_data:
            for _ in range(deck_card.quantity):
                expanded_cards.append({
                    "card_data": full_data,
                    "board": deck_card.board,
                    "quantity": deck_card.quantity,
                })
        else:
            not_found.append(deck_card.card_name)

    # --- Compute all analytics ---
    mana_curve = _compute_mana_curve(expanded_cards)
    color_distribution = _compute_color_distribution(expanded_cards)
    type_distribution = _compute_type_distribution(expanded_cards)
    mana_base = _compute_mana_base(expanded_cards)
    avg_cmc = _compute_average_cmc(expanded_cards)
    composition = _compute_composition(deck_cards)
    deck_identity = _compute_deck_identity(type_distribution)

    result = {
        "total_cards": sum(c.quantity for c in deck_cards),
        "unique_cards": len(deck_cards),
        "cards_not_found": not_found,
        "mana_curve": mana_curve,
        "color_distribution": color_distribution,
        "type_distribution": type_distribution,
        "mana_base": mana_base,
        "average_cmc": avg_cmc,
        "composition": composition,
        "deck_identity": deck_identity,
    }

    # Include card lookup for AI context if requested
    if include_card_data:
        result["_card_lookup"] = card_lookup

    return result


def _compute_mana_curve(expanded_cards: list) -> dict:
    """Count non-land cards at each CMC from 0 to 7+."""
    curve = {str(i): 0 for i in range(8)}

    for entry in expanded_cards:
        card = entry["card_data"]
        type_line = card.get("type_line", "")

        if "Land" in type_line:
            continue

        cmc = int(card.get("cmc", 0))
        if cmc >= 7:
            curve["7+"] = curve.get("7+", 0) + 1
        else:
            curve[str(cmc)] = curve.get(str(cmc), 0) + 1

    if "7" in curve and "7+" not in curve:
        curve["7+"] = curve.pop("7")
    elif "7" in curve and "7+" in curve:
        curve["7+"] += curve.pop("7")

    return curve


def _compute_color_distribution(expanded_cards: list) -> dict:
    """Count mana symbols by color across all non-land cards."""
    distribution = {c: 0 for c in COLORS}

    for entry in expanded_cards:
        card = entry["card_data"]
        mana_cost = card.get("mana_cost", "")

        if not mana_cost:
            continue

        symbols = MANA_SYMBOL_PATTERN.findall(mana_cost)
        for symbol in symbols:
            parts = symbol.split("/")
            for part in parts:
                if part in COLORS:
                    distribution[part] += 1

    result = {}
    for color in COLORS:
        result[color] = {
            "name": COLOR_NAMES[color],
            "count": distribution[color],
        }

    return result


def _compute_type_distribution(expanded_cards: list) -> dict:
    """Count cards by type category."""
    distribution = {t: 0 for t in TYPE_CATEGORIES}
    other = 0

    for entry in expanded_cards:
        card = entry["card_data"]
        type_line = card.get("type_line", "")

        matched = False
        for type_cat in TYPE_CATEGORIES:
            if type_cat in type_line:
                distribution[type_cat] += 1
                matched = True
                break

        if not matched:
            other += 1

    if other > 0:
        distribution["Other"] = other

    return distribution


def _compute_mana_base(expanded_cards: list) -> dict:
    """Analyze the mana base — land count, color sources, fixing."""
    total_cards = len(expanded_cards)
    lands = []
    non_lands = []

    for entry in expanded_cards:
        card = entry["card_data"]
        type_line = card.get("type_line", "")
        if "Land" in type_line:
            lands.append(card)
        else:
            non_lands.append(card)

    land_count = len(lands)

    color_sources = {c: 0 for c in COLORS}
    for land in lands:
        color_identity = land.get("color_identity", [])
        oracle = land.get("oracle_text", "").lower()

        for color in COLORS:
            color_lower = {"W": "white", "U": "blue", "B": "black", "R": "red", "G": "green"}
            if color in color_identity:
                color_sources[color] += 1
            elif color_lower[color] in oracle or f"add {{{color.lower()}}}" in oracle:
                color_sources[color] += 1

    return {
        "land_count": land_count,
        "non_land_count": len(non_lands),
        "land_percentage": round((land_count / total_cards * 100), 1) if total_cards > 0 else 0,
        "color_sources": color_sources,
    }


def _compute_average_cmc(expanded_cards: list) -> float:
    """Average CMC of non-land cards."""
    non_land_cmcs = []

    for entry in expanded_cards:
        card = entry["card_data"]
        type_line = card.get("type_line", "")
        if "Land" not in type_line:
            non_land_cmcs.append(card.get("cmc", 0))

    if not non_land_cmcs:
        return 0.0

    return round(sum(non_land_cmcs) / len(non_land_cmcs), 2)


def _compute_composition(deck_cards: list) -> dict:
    """Summary of deck composition by board."""
    composition = {"main": 0, "sideboard": 0, "commander": 0}

    for card in deck_cards:
        board = card.board if card.board in composition else "main"
        composition[board] += card.quantity

    composition["total"] = sum(composition.values())
    return composition

def _compute_deck_identity(type_distribution: dict) -> dict:
    """Determine the deck's primary identity based on non-land card types."""
    non_land = {t: c for t, c in type_distribution.items() if t != "Land" and c > 0}
    total_non_land = sum(non_land.values())
    
    if total_non_land == 0:
        return {"primary_type": "unknown", "percentages": {}, "recommendation_weight": "balanced"}
    
    percentages = {t: round(c / total_non_land * 100, 1) for t, c in non_land.items()}
    sorted_types = sorted(percentages.items(), key=lambda x: -x[1])
    primary_type = sorted_types[0][0] if sorted_types else "unknown"
    primary_pct = sorted_types[0][1] if sorted_types else 0
    
    # Determine recommendation weight
    if primary_pct >= 50:
        weight = f"heavily {primary_type.lower()}-based"
    elif primary_pct >= 35:
        weight = f"primarily {primary_type.lower()}-based"
    else:
        weight = "balanced"
    
    # Count spells vs permanents
    spell_types = {"Instant", "Sorcery"}
    permanent_types = {"Creature", "Enchantment", "Artifact", "Planeswalker"}
    
    spell_count = sum(type_distribution.get(t, 0) for t in spell_types)
    permanent_count = sum(type_distribution.get(t, 0) for t in permanent_types)
    
    return {
        "primary_nonland_type": primary_type,
        "primary_nonland_percentage": primary_pct,
        "type_percentages": dict(sorted_types),
        "recommendation_weight": weight,
        "spell_count": spell_count,
        "permanent_count": permanent_count,
        "spell_vs_permanent": "spell-heavy" if spell_count > permanent_count else "permanent-heavy",
    }

def _empty_analytics() -> dict:
    """Return empty analytics structure for an empty deck."""
    return {
        "total_cards": 0,
        "unique_cards": 0,
        "cards_not_found": [],
        "mana_curve": {str(i): 0 for i in range(7)} | {"7+": 0},
        "color_distribution": {c: {"name": COLOR_NAMES[c], "count": 0} for c in COLORS},
        "type_distribution": {t: 0 for t in TYPE_CATEGORIES},
        "mana_base": {"land_count": 0, "non_land_count": 0, "land_percentage": 0, "color_sources": {c: 0 for c in COLORS}},
        "average_cmc": 0.0,
        "composition": {"main": 0, "sideboard": 0, "commander": 0, "total": 0},
    }