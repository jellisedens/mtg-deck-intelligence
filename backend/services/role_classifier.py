"""
AI-powered card role classifier.
Classifies each card in a deck by its strategic role.
"""

import os
import json
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL = "gpt-4o-mini"

STRATEGIC_ROLES = [
    "ramp",
    "card_draw",
    "removal",
    "board_wipe",
    "counterspell",
    "protection",
    "tribal_synergy",
    "win_condition",
    "combo_piece",
    "utility",
    "mana_fixing",
    "cost_reducer",
    "token_generator",
    "graveyard",
    "tutor",
    "land",
]


def classify_deck_roles(deck_cards: list, card_lookup: dict, deck_info: dict = None) -> dict:
    """
    Classify each card in the deck by strategic role using AI.

    Args:
        deck_cards: list of DeckCard ORM objects
        card_lookup: dict of scryfall_id → full card data (from analytics)
        deck_info: optional dict with deck name, format, description

    Returns:
        dict with role_distribution and per-card roles
    """
    # Build card summaries for the AI
    card_summaries = []
    for deck_card in deck_cards:
        full_data = card_lookup.get(deck_card.scryfall_id, {})
        oracle = full_data.get("oracle_text", "")
        type_line = full_data.get("type_line", "")
        keywords = full_data.get("keywords", [])

        card_summaries.append({
            "name": deck_card.card_name,
            "type_line": type_line,
            "oracle_text": oracle[:200],
            "keywords": keywords,
            "quantity": deck_card.quantity,
            "board": deck_card.board,
        })

    # Determine primary creature type from deck
    creature_types = {}
    for deck_card in deck_cards:
        full_data = card_lookup.get(deck_card.scryfall_id, {})
        type_line = full_data.get("type_line", "")
        if "Creature" in type_line:
            parts = type_line.split("—")
            if len(parts) > 1:
                subtypes = parts[1].strip().split()
                for subtype in subtypes:
                    creature_types[subtype] = creature_types.get(subtype, 0) + deck_card.quantity

    primary_type = max(creature_types, key=creature_types.get) if creature_types else None

    # Build context
    context = ""
    if deck_info:
        context += f"Deck: {deck_info.get('name', 'Unknown')}\n"
        context += f"Format: {deck_info.get('format', 'Unknown')}\n"
        if deck_info.get("description"):
            context += f"Strategy: {deck_info['description']}\n"
    if primary_type:
        context += f"Primary creature type: {primary_type}\n"

    system = f"""You are an expert MTG deck analyst. Classify each card by its PRIMARY strategic role.

Available roles: {json.dumps(STRATEGIC_ROLES)}

Rules:
- Each card gets exactly ONE primary role (its most important function in this specific deck)
- A card can also have secondary roles listed separately
- Lands are ALWAYS role "land" — no exceptions. If a card's type_line contains "Land", its primary_role MUST be "land". Use secondary_roles to capture additional functions (e.g., a land that also fixes mana gets primary_role "land" and secondary_roles ["mana_fixing"])- Cards that reference the deck's primary creature type ({primary_type or 'none'}) and provide
  a bonus to that type should be tagged as "tribal_synergy"
- Mana dorks and mana rocks are "ramp"
- Cards that say "search your library" are "tutor"
- Cards that reduce costs are "cost_reducer"
- Cards that draw cards or provide card advantage are "card_draw"
- Cards that destroy/exile/damage permanents are "removal"
- Cards that destroy ALL or affect ALL are "board_wipe"
- Consider what the card DOES IN THIS DECK, not in a vacuum

Respond with ONLY valid JSON (no markdown):
{{
    "card_roles": [
        {{
            "name": "Card Name",
            "primary_role": "role",
            "secondary_roles": ["role2"],
            "synergy_notes": "brief note on how it synergizes with the deck"
        }}
    ]
}}"""

    # Split into batches to avoid token limits
    all_roles = []
    batch_size = 30

    for i in range(0, len(card_summaries), batch_size):
        batch = card_summaries[i:i + batch_size]

        user_msg = f"Deck context:\n{context}\n\nClassify these cards:\n"
        for card in batch:
            user_msg += f"- {card['name']} | {card['type_line']} | {card['oracle_text'][:150]}\n"

        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_msg},
                ],
                temperature=0.1,
            )

            content = response.choices[0].message.content.strip()
            content = content.replace("```json", "").replace("```", "").strip()
            parsed = json.loads(content)
            all_roles.extend(parsed.get("card_roles", []))

        except Exception as e:
            # If classification fails for a batch, continue with others
            for card in batch:
                all_roles.append({
                    "name": card["name"],
                    "primary_role": "utility",
                    "secondary_roles": [],
                    "synergy_notes": "classification failed",
                })

    # Build role distribution — count both primary and secondary roles
    role_distribution = {role: 0 for role in STRATEGIC_ROLES}
    for card_role in all_roles:
        primary = card_role.get("primary_role", "utility")
        secondary = card_role.get("secondary_roles", [])
        
        # Find matching deck card for quantity
        matching = [dc for dc in deck_cards if dc.card_name.lower() == card_role["name"].lower()]
        qty = matching[0].quantity if matching else 1
        
        # Count primary role
        if primary in role_distribution:
            role_distribution[primary] += qty
        else:
            role_distribution["utility"] += qty
        
        # Count secondary roles too
        for sec_role in secondary:
            if sec_role in role_distribution and sec_role != primary:
                role_distribution[sec_role] += qty

    return {
        "role_distribution": role_distribution,
        "card_roles": all_roles,
        "primary_creature_type": primary_type,
    }