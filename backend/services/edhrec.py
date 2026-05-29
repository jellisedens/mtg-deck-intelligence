"""
EDHREC integration service.
Fetches commander-specific card popularity and synergy data.
"""

import httpx
import logging
from typing import Optional

logger = logging.getLogger(__name__)

EDHREC_BASE = "https://json.edhrec.com/pages/commanders"


def _commander_slug(name: str) -> str:
    """Convert commander name to EDHREC URL slug."""
    return (
        name.lower()
        .replace(",", "")
        .replace("'", "")
        .replace("'", "")
        .replace(".", "")
        .replace("!", "")
        .replace(":", "")
        .strip()
        .replace(" ", "-")
    )


async def fetch_commander_profile(commander_name: str) -> Optional[dict]:
    """
    Fetch EDHREC data for a commander and return a structured profile.
    Returns None if commander not found or request fails.
    """
    slug = _commander_slug(commander_name)
    url = f"{EDHREC_BASE}/{slug}.json"

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                url,
                headers={"User-Agent": "MTGDeckIntelligence/1.0"},
                timeout=15,
            )
            if resp.status_code != 200:
                logger.warning(f"EDHREC returned {resp.status_code} for {slug}")
                return None

            data = resp.json()
    except Exception as e:
        logger.warning(f"EDHREC fetch failed for {slug}: {e}")
        return None

    # Parse the response
    container = data.get("container", {})
    json_dict = container.get("json_dict", {})
    card_info = json_dict.get("card", {})
    cardlists = json_dict.get("cardlists", [])

    total_decks = card_info.get("num_decks", 0)
    if not total_decks:
        return None

    # Collect all cards across all categories
    all_cards = []
    seen_names = set()

    # Map EDHREC categories to our tags
    category_map = {
        "highsynergycards": "high_synergy",
        "topcards": "top",
        "newcards": "new",
        "gamechangers": "game_changer",
        "creatures": "creature",
        "instants": "instant",
        "sorceries": "sorcery",
        "utilityartifacts": "artifact",
        "enchantments": "enchantment",
        "planeswalkers": "planeswalker",
        "utilitylands": "utility_land",
        "manaartifacts": "mana_artifact",
        "lands": "land",
    }

    for cardlist in cardlists:
        tag = cardlist.get("tag", "")
        category = category_map.get(tag, tag)
        
        for card in cardlist.get("cardviews", []):
            name = card.get("name", "")
            if not name or name in seen_names:
                continue
            seen_names.add(name)

            inclusion = card.get("num_decks", 0)
            pct = round((inclusion / total_decks) * 100, 1) if total_decks else 0

            all_cards.append({
                "name": name,
                "inclusion_pct": pct,
                "synergy": card.get("synergy", 0),
                "category": category,
                "trend": round(card.get("trend_zscore", 0), 2),
            })

    # Sort by inclusion percentage descending
    all_cards.sort(key=lambda c: c["inclusion_pct"], reverse=True)

    # Get theme tags
    panel = data.get("panel", {})
    themes = [
        {"name": t["value"], "count": t["count"]}
        for t in panel.get("taglinks", [])[:10]
    ]

    # Get combo data
    combos = [
        c["value"]
        for c in panel.get("combocounts", [])
        if c.get("value") != "See More..."
    ]

    return {
        "commander_name": commander_name,
        "edhrec_slug": slug,
        "total_decks": total_decks,
        "rank": card_info.get("rank"),
        "salt": card_info.get("salt"),
        "themes": themes,
        "combos": combos,
        "cards": all_cards,
    }


def get_missing_staples(profile: dict, deck_card_names: list, min_inclusion_pct: float = 50) -> list:
    """
    Return cards from the EDHREC profile that the deck is missing,
    filtered by minimum inclusion percentage.
    """
    if not profile:
        return []

    deck_names = {n.lower() for n in deck_card_names}
    missing = []

    for card in profile.get("cards", []):
        if card["name"].lower() not in deck_names and card["inclusion_pct"] >= min_inclusion_pct:
            missing.append(card)

    return missing


def get_synergy_cards(profile: dict, deck_card_names: list, min_synergy: float = 0.3) -> list:
    """
    Return high-synergy cards from the EDHREC profile that the deck is missing.
    These are commander-specific picks, not generic staples.
    """
    if not profile:
        return []

    deck_names = {n.lower() for n in deck_card_names}
    synergy_cards = []

    for card in profile.get("cards", []):
        if (card["name"].lower() not in deck_names 
                and card.get("synergy", 0) >= min_synergy):
            synergy_cards.append(card)

    synergy_cards.sort(key=lambda c: c["synergy"], reverse=True)
    return synergy_cards


def format_edhrec_context_for_prompt(profile: dict, deck_card_names: list, max_cards: int = 20) -> str:
    """
    Format EDHREC data for injection into AI suggest prompts.
    Shows what the deck is missing that the community recommends.
    """
    if not profile:
        return ""

    missing = get_missing_staples(profile, deck_card_names, min_inclusion_pct=40)
    if not missing:
        return ""

    lines = [
        f"EDHREC COMMUNITY DATA ({profile['total_decks']} decks analyzed for {profile['commander_name']}):",
        f"Cards most {profile['commander_name']} decks run that THIS deck is missing:",
    ]

    for card in missing[:max_cards]:
        synergy_note = f", synergy: {card['synergy']}" if card.get("synergy", 0) > 0.3 else ""
        lines.append(f"  - {card['name']} ({card['inclusion_pct']}% of decks{synergy_note})")

    lines.append("")
    lines.append("HIGH SYNERGY cards are specifically good with this commander, not just generic staples.")
    lines.append("Prioritize high-synergy cards over generic staples when both fit the user's request.")

    return "\n".join(lines)