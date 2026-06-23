"""
Card Tagger — unified tag-based card classification.

Tags any card by oracle_id using the bulk tag index.
Falls back to oracle text matching for untagged cards.
Used by: analytics, deck intelligence, cuts, swap, simulation.
"""

from services.tag_index import get_card_tags, is_index_loaded
from data.scryfall_tags import CATEGORY_TAG_GROUPS, ORACLE_FALLBACKS


def get_card_roles(oracle_id: str, oracle_text: str = "", type_line: str = "") -> list:
    """
    Get functional roles for a card.
    Tags first, oracle text fallback for untagged cards.
    
    Returns list of category keys like ["ramp", "mana_rocks"]
    """
    tags = get_card_tags(oracle_id) if is_index_loaded() else []
    roles = []

    for category, tag_group in CATEGORY_TAG_GROUPS.items():
        if not tag_group:
            continue
        tags_lower = [t.lower() for t in tags]
        if any(g.lower() in tags_lower for g in tag_group):
            if category not in roles:
                roles.append(category)

    # Oracle text fallback for untagged cards
    if not roles and oracle_text:
        text_lower = oracle_text.lower()
        for category, hints in ORACLE_FALLBACKS.items():
            if any(h.lower() in text_lower for h in hints):
                if category not in roles:
                    roles.append(category)

    # Type-line based roles (always apply, supplements tags)
    if type_line:
        type_lower = type_line.lower()
        if "land" in type_lower and "land" not in [r for r in roles if "land" in r]:
            roles.append("land")
        if "equipment" in type_lower and "equipment" not in roles:
            roles.append("equipment")

    # Basic lands are NOT ramp/rocks/dorks — they're just lands
    if type_line and "basic land" in type_line.lower():
        roles = [r for r in roles if r in ("land",)]

    return roles


async def get_role_tags_for_deck(deck_cards: list) -> dict:
    """
    Fetch Scryfall data for a deck and compute canonical role tags per card.
    Used by the deck view to display auto-detected tags (ramp, removal, draw, etc.)
    """
    from services.scryfall import scryfall_service

    if not deck_cards:
        return {"tags": {}, "counts": {}, "untagged": []}

    identifiers = [{"id": c.scryfall_id} for c in deck_cards]
    scryfall_data = await scryfall_service.get_collection(identifiers)
    if "error" in scryfall_data:
        return {"tags": {}, "counts": {}, "untagged": [c.card_name for c in deck_cards]}

    card_lookup = {c["id"]: c for c in scryfall_data.get("data", [])}
    role_dist = get_deck_role_distribution(deck_cards, card_lookup)

    return {
        "tags": role_dist["card_roles"],
        "counts": role_dist["counts"],
        "untagged": role_dist["untagged"],
    }


def get_deck_role_distribution(deck_cards: list, card_lookup: dict) -> dict:
    """
    Get role counts and per-card roles for an entire deck.
    
    Returns:
    {
        "counts": {"ramp": 7, "removal": 3, "draw": 2, "land": 35, ...},
        "card_roles": {
            "Sol Ring": ["ramp", "mana_rocks"],
            "Path to Exile": ["removal", "spot_removal"],
            ...
        },
        "untagged": ["Card Name", ...],  # cards with no roles found
        "total_cards": 99,
    }
    """
    counts = {}
    card_roles = {}
    untagged = []
    total = 0

    for card in deck_cards:
        data = card_lookup.get(card.scryfall_id, {})
        oracle_id = data.get("oracle_id", "")
        oracle_text = data.get("oracle_text", "")
        type_line = data.get("type_line", "")

        roles = get_card_roles(oracle_id, oracle_text, type_line)

        if roles:
            card_roles[card.card_name] = roles
            for role in roles:
                counts[role] = counts.get(role, 0) + card.quantity
        else:
            untagged.append(card.card_name)

        total += card.quantity

    return {
        "counts": counts,
        "card_roles": card_roles,
        "untagged": untagged,
        "total_cards": total,
    }


# Recommended minimums for a Commander deck
COMMANDER_ROLE_TARGETS = {
    "ramp": 10,
    "removal": 8,
    "spot_removal": 5,
    "board_wipe": 3,
    "draw": 10,
    "protection": 4,
    "land": 36,
}


def get_deck_gaps(role_distribution: dict, targets: dict = None) -> list:
    """
    Compare deck role counts against recommended targets.
    
    Returns list of gaps:
    [
        {"role": "draw", "have": 2, "target": 10, "gap": -8, "priority": "critical"},
        {"role": "ramp", "have": 7, "target": 10, "gap": -3, "priority": "moderate"},
    ]
    """
    if targets is None:
        targets = COMMANDER_ROLE_TARGETS

    counts = role_distribution.get("counts", {})
    gaps = []

    for role, target in targets.items():
        have = counts.get(role, 0)
        gap = have - target
        if gap < 0:
            if gap <= -5:
                priority = "critical"
            elif gap <= -2:
                priority = "moderate"
            else:
                priority = "low"
            gaps.append({
                "role": role,
                "have": have,
                "target": target,
                "gap": gap,
                "priority": priority,
            })

    # Sort by priority (critical first)
    priority_order = {"critical": 0, "moderate": 1, "low": 2}
    gaps.sort(key=lambda g: (priority_order.get(g["priority"], 3), g["gap"]))

    return gaps


def format_deck_intelligence(role_distribution: dict, gaps: list) -> str:
    """
    Format deck intelligence for injection into AI prompts.
    """
    counts = role_distribution.get("counts", {})
    total = role_distribution.get("total_cards", 0)

    lines = [f"DECK COMPOSITION ({total} cards):"]

    # Role counts
    display_roles = [
        ("land", "Lands"),
        ("ramp", "Ramp"),
        ("draw", "Card Draw"),
        ("removal", "Removal"),
        ("spot_removal", "  Spot Removal"),
        ("board_wipe", "  Board Wipes"),
        ("protection", "Protection"),
        ("counterspell", "Counterspells"),
        ("lifegain", "Lifegain"),
        ("lifegain_payoff", "Lifegain Payoffs"),
        ("tutor", "Tutors"),
        ("sacrifice", "Sacrifice Outlets"),
        ("recursion", "Recursion"),
        ("evasion", "Evasion"),
    ]

    for role_key, display_name in display_roles:
        count = counts.get(role_key, 0)
        if count > 0 or role_key in COMMANDER_ROLE_TARGETS:
            target = COMMANDER_ROLE_TARGETS.get(role_key)
            if target:
                status = "✓" if count >= target else "✗"
                lines.append(f"  {display_name}: {count}/{target} {status}")
            else:
                lines.append(f"  {display_name}: {count}")

    # Gaps
    if gaps:
        lines.append("\nDECK GAPS (priority order):")
        for gap in gaps:
            lines.append(f"  {gap['role'].replace('_', ' ').title()}: need {abs(gap['gap'])} more ({gap['priority']})")

    return "\n".join(lines)