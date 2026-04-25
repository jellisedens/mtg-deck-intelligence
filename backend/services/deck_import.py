"""
Deck import service.
Supports importing decks from Archidekt and plain text lists.
"""

import re
import httpx
from services.scryfall import scryfall_service


# Archidekt format codes to our format strings
ARCHIDEKT_FORMATS = {
    1: "standard",
    2: "modern",
    3: "commander",
    4: "legacy",
    5: "vintage",
    6: "pauper",
    7: "pioneer",
    8: "oathbreaker",
    9: "brawl",
}


async def import_from_archidekt(deck_url: str) -> dict:
    """
    Import a deck from Archidekt.

    Args:
        deck_url: Archidekt URL (https://archidekt.com/decks/123456) or just the deck ID

    Returns:
        {
            "name": "Deck Name",
            "format": "commander",
            "description": "...",
            "cards": [
                {"card_name": "Sol Ring", "scryfall_id": "xxx", "quantity": 1, "board": "main"},
                ...
            ],
            "errors": ["Card X not found on Scryfall", ...]
        }
    """
    # Extract deck ID from URL or raw ID
    deck_id = _extract_archidekt_id(deck_url)
    if not deck_id:
        return {"error": "Invalid Archidekt URL or deck ID. Expected format: https://archidekt.com/decks/123456 or just 123456"}

    # Fetch deck from Archidekt API
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"https://archidekt.com/api/decks/{deck_id}/",
                timeout=15.0,
            )

            if resp.status_code == 404:
                return {"error": f"Deck {deck_id} not found on Archidekt. Make sure the deck is public."}

            if resp.status_code != 200:
                return {"error": f"Archidekt API returned status {resp.status_code}"}

            data = resp.json()

    except httpx.TimeoutException:
        return {"error": "Archidekt API timed out. Try again later."}
    except Exception as e:
        return {"error": f"Failed to fetch deck from Archidekt: {str(e)}"}

    # Parse deck metadata
    deck_name = data.get("name", "Imported Deck")
    format_code = data.get("deckFormat", 3)
    deck_format = ARCHIDEKT_FORMATS.get(format_code, "commander")

    # Parse description (Archidekt stores it as rich text JSON)
    description = ""
    raw_desc = data.get("description", "")
    if isinstance(raw_desc, str):
        try:
            import json
            desc_data = json.loads(raw_desc)
            if isinstance(desc_data, dict) and "ops" in desc_data:
                parts = []
                for op in desc_data["ops"]:
                    if isinstance(op, dict) and "insert" in op:
                        text = op["insert"].strip()
                        if text and text != "Add a description...":
                            parts.append(text)
                description = " ".join(parts)
        except (json.JSONDecodeError, TypeError):
            description = raw_desc if raw_desc != '{"ops": [{"insert": "Add a description..."}]}' else ""

    # Parse cards
    raw_cards = data.get("cards", [])
    parsed_cards = []
    errors = []
    scryfall_ids_to_verify = []

    for entry in raw_cards:
        card_data = entry.get("card", {})
        oracle_data = card_data.get("oracleCard", {})

        card_name = oracle_data.get("name") or card_data.get("displayName")
        scryfall_id = card_data.get("uid")
        quantity = entry.get("quantity", 1)
        categories = entry.get("categories") or []

        if not card_name:
            errors.append(f"Skipped card with no name (UID: {scryfall_id})")
            continue

        if not scryfall_id:
            errors.append(f"Skipped {card_name} - no Scryfall ID")
            continue

        # Determine board from Archidekt categories
        board = "main"
        categories_lower = [c.lower() for c in categories]
        if "commander" in categories_lower:
            board = "commander"
        elif "sideboard" in categories_lower:
            board = "sideboard"
        elif "maybeboard" in categories_lower:
            continue  # Skip maybeboard cards

        parsed_cards.append({
            "card_name": card_name,
            "scryfall_id": scryfall_id,
            "quantity": quantity,
            "board": board,
        })
        scryfall_ids_to_verify.append({"id": scryfall_id})

    # Verify cards exist on Scryfall using collection endpoint
    if scryfall_ids_to_verify:
        verified = await _verify_scryfall_ids(scryfall_ids_to_verify)
        verified_ids = set(verified.keys())

        final_cards = []
        for card in parsed_cards:
            if card["scryfall_id"] in verified_ids:
                # Use Scryfall's canonical name
                card["card_name"] = verified[card["scryfall_id"]]
                final_cards.append(card)
            else:
                # Try fuzzy name match as fallback
                fallback = await _find_card_by_name(card["card_name"])
                if fallback:
                    card["scryfall_id"] = fallback["id"]
                    card["card_name"] = fallback["name"]
                    final_cards.append(card)
                else:
                    errors.append(f"Could not verify {card['card_name']} on Scryfall")

        parsed_cards = final_cards

    return {
        "name": deck_name,
        "format": deck_format,
        "description": description,
        "cards": parsed_cards,
        "errors": errors,
        "source": "archidekt",
        "source_id": str(deck_id),
    }


async def import_from_text(deck_text: str, deck_format: str = "commander") -> dict:
    """
    Import a deck from a plain text list.
    Supports formats like:
        1x Sol Ring
        1 Sol Ring
        Sol Ring
        
    Commander can be marked with:
        1x The Ur-Dragon *CMDR*
        // Commander
        1x The Ur-Dragon

    Returns same format as import_from_archidekt.
    """
    lines = deck_text.strip().split("\n")
    parsed_cards = []
    errors = []
    current_board = "main"

    for line in lines:
        line = line.strip()
        if not line or line.startswith("//"):
            # Check for section headers
            line_lower = line.lower()
            if "commander" in line_lower:
                current_board = "commander"
            elif "sideboard" in line_lower:
                current_board = "sideboard"
            elif "main" in line_lower or "deck" in line_lower:
                current_board = "main"
            continue

        # Parse quantity and card name
        quantity, card_name, board_override = _parse_text_line(line)

        if not card_name:
            continue

        board = board_override or current_board

        parsed_cards.append({
            "card_name": card_name,
            "scryfall_id": None,  # Will be resolved
            "quantity": quantity,
            "board": board,
        })

    # Resolve all card names to Scryfall IDs
    resolved_cards = []
    for card in parsed_cards:
        result = await _find_card_by_name(card["card_name"])
        if result:
            card["scryfall_id"] = result["id"]
            card["card_name"] = result["name"]  # Use canonical name
            resolved_cards.append(card)
        else:
            errors.append(f"Card not found: {card['card_name']}")

    return {
        "name": "Imported Deck",
        "format": deck_format,
        "description": "",
        "cards": resolved_cards,
        "errors": errors,
        "source": "text",
        "source_id": None,
    }


def _extract_archidekt_id(url_or_id: str) -> int | None:
    """Extract the numeric deck ID from an Archidekt URL or raw ID."""
    url_or_id = url_or_id.strip()

    # Direct numeric ID
    if url_or_id.isdigit():
        return int(url_or_id)

    # URL patterns
    patterns = [
        r"archidekt\.com/decks/(\d+)",
        r"archidekt\.com/api/decks/(\d+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, url_or_id)
        if match:
            return int(match.group(1))

    return None


def _parse_text_line(line: str) -> tuple:
    """
    Parse a single line from a text deck list.
    Returns (quantity, card_name, board_override).
    """
    board_override = None

    # Check for commander marker
    if "*CMDR*" in line.upper() or "*COMMANDER*" in line.upper():
        board_override = "commander"
        line = re.sub(r'\*CMDR\*|\*COMMANDER\*', '', line, flags=re.IGNORECASE).strip()

    # Pattern: "1x Card Name" or "1 Card Name"
    match = re.match(r'^(\d+)x?\s+(.+)$', line)
    if match:
        return int(match.group(1)), match.group(2).strip(), board_override

    # Pattern: just "Card Name" (assume quantity 1)
    if line and not line[0].isdigit():
        return 1, line.strip(), board_override

    return 0, None, None


async def _verify_scryfall_ids(identifiers: list) -> dict:
    """
    Verify a list of Scryfall IDs and return {id: canonical_name} mapping.
    """
    result = await scryfall_service.get_collection(identifiers)
    if "error" in result:
        return {}

    return {
        card["id"]: card["name"]
        for card in result.get("data", [])
    }


async def _find_card_by_name(name: str) -> dict | None:
    """
    Find a card by name using Scryfall's exact/fuzzy search.
    Returns {"id": scryfall_id, "name": canonical_name} or None.
    """
    # Try exact match first
    result = await scryfall_service.get_card_by_name(name, fuzzy=False)
    if result and "error" not in result:
        return {"id": result["id"], "name": result["name"]}

    # Try fuzzy match
    result = await scryfall_service.get_card_by_name(name, fuzzy=True)
    if result and "error" not in result:
        return {"id": result["id"], "name": result["name"]}

    return None