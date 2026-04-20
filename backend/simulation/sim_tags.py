"""
AI-powered simulation tag generator.
Reads oracle text and generates structured mechanical tags
that the simulator can execute.
"""

import os
import json
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL = "gpt-4o-mini"


def generate_sim_tags(deck_cards: list, card_lookup: dict) -> dict:
    """
    Generate simulation tags for each card in the deck.

    Args:
        deck_cards: list of DeckCard ORM objects
        card_lookup: dict of scryfall_id → full Scryfall card data

    Returns:
        dict of card_name (lowercase) → sim_tags
    """
    # Build card summaries
    card_summaries = []
    for deck_card in deck_cards:
        full_data = card_lookup.get(deck_card.scryfall_id, {})
        card_summaries.append({
            "name": deck_card.card_name,
            "mana_cost": full_data.get("mana_cost", ""),
            "cmc": full_data.get("cmc", 0),
            "type_line": full_data.get("type_line", ""),
            "oracle_text": full_data.get("oracle_text", ""),
            "colors": full_data.get("colors", []),
            "color_identity": full_data.get("color_identity", []),
            "power": full_data.get("power"),
            "toughness": full_data.get("toughness"),
            "keywords": full_data.get("keywords", []),
            "produced_mana": full_data.get("produced_mana", []),
        })

    system = """You are a Magic: The Gathering rules engine. For each card, generate structured
simulation tags that describe its mechanical effects in a format a game simulator can execute.

Respond with ONLY valid JSON (no markdown, no backticks):
{{
    "cards": [
        {{
            "name": "Card Name",
            "sim_tags": {{
                "cast_cost": {{"total": 3, "colors": {{"G": 1}}}},
                "is_land": false,
                "permanent": true,
                "enters_tapped": false,
                "mana_production": null or {{
                    "type": "tap",
                    "produces": {{"R": 1}} or null,
                    "produces_choice": ["R", "G"] or null,
                    "produces_any": false,
                    "amount": 1
                }},
                "on_resolve": [
                    list of actions executed when the card is cast/played
                ],
                "on_etb": [
                    list of actions executed when the permanent enters the battlefield
                ],
                "on_attack": [
                    list of actions when this creature attacks
                ],
                "power": 5 or null,
                "toughness": 5 or null,
                "static_effects": [
                    list of ongoing effects while on the battlefield
                ]
            }}
        }}
    ]
}}

AVAILABLE ACTIONS for on_resolve, on_etb, on_attack:
- {{"action": "draw", "count": N}}
- {{"action": "put_back", "count": N, "destination": "top_of_library"}}
- {{"action": "search_land", "count": N, "destination": "battlefield" or "hand", "enters_tapped": true/false, "land_type": "basic" or "forest" or "any" or "nonbasic"}}
- {{"action": "shuffle_library"}}
- {{"action": "create_token", "count": N, "token": {{"type": "Treasure"}} or {{"type": "Creature", "power": N, "toughness": N}}}}
- {{"action": "add_mana", "mana": {{"R": 1, "G": 1}}}}
- {{"action": "destroy", "target": "creature" or "artifact" or "enchantment" or "any"}}
- {{"action": "exile", "target": "creature" or "any"}}
- {{"action": "return_to_hand", "target": "creature" or "nonland"}}
- {{"action": "discard", "count": N}}
- {{"action": "mill", "count": N}}
- {{"action": "scry", "count": N}}
- {{"action": "gain_life", "amount": N}}
- {{"action": "deal_damage", "amount": N, "target": "any" or "creature" or "player"}}

AVAILABLE STATIC EFFECTS:
- {{"effect": "cost_reduction", "applies_to": "dragon" or "creature" or "all", "amount": 1}}
- {{"effect": "anthem", "applies_to": "creature" or "dragon", "power_bonus": 1, "toughness_bonus": 1}}
- {{"effect": "haste", "applies_to": "dragon" or "creature" or "self"}}
- {{"effect": "mana_doubling"}}
- {{"effect": "draw_on_creature_etb", "condition": "power_4_or_greater" or "any"}}
- {{"effect": "draw_on_combat_damage"}}
- {{"effect": "lands_produce_any_color"}}
- {{"effect": "additional_land_drop", "count": 1}}
- {{"effect": "no_max_hand_size"}}

RULES:
- cast_cost is null for lands
- is_land is true only for Land type cards
- permanent is true for creatures, enchantments, artifacts, planeswalkers
- permanent is false for instants and sorceries
- For mana rocks/dorks: set mana_production with what they tap for
- For lands: always set mana_production
  - Single color land: produces: {{"G": 1}}
  - Dual land (choose one): produces_choice: ["R", "G"]
  - Any color land (Command Tower): produces_any: true
  - Basic lands: produces the matching color
- enters_tapped: check oracle text for "enters the battlefield tapped" or "enters tapped"
  - Shock lands: enters_tapped_unless pay 2 life — for simulation treat as untapped (assume pay life)
  - Check lands, temple lands: enters tapped
- For fetch lands (sacrifice, search): on_etb or activated ability with search_land + shuffle
- power/toughness: include for creatures, null for non-creatures
- on_resolve: for instants/sorceries — what happens when cast
- on_etb: for permanents — what happens when entering the battlefield
- on_attack: for creatures — what happens when attacking
- Simplify complex effects — capture the primary mechanical impact
- If a card has multiple modes, capture the most commonly chosen mode
"""

    all_tags = {}
    batch_size = 25

    for i in range(0, len(card_summaries), batch_size):
        batch = card_summaries[i:i + batch_size]

        user_msg = "Generate simulation tags for these cards:\n\n"
        for card in batch:
            user_msg += f"Name: {card['name']}\n"
            user_msg += f"Mana Cost: {card['mana_cost']}\n"
            user_msg += f"CMC: {card['cmc']}\n"
            user_msg += f"Type: {card['type_line']}\n"
            user_msg += f"Oracle: {card['oracle_text']}\n"
            user_msg += f"Power/Toughness: {card['power']}/{card['toughness']}\n"
            user_msg += f"Keywords: {card['keywords']}\n"
            user_msg += f"Produced Mana: {card['produced_mana']}\n"
            user_msg += f"Color Identity: {card['color_identity']}\n\n"

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

            for card_data in parsed.get("cards", []):
                name = card_data.get("name", "").lower()
                all_tags[name] = card_data.get("sim_tags", {})

        except Exception as e:
            print(f"  Sim tag generation error: {type(e).__name__}: {e}")
            for card in batch:
                all_tags[card["name"].lower()] = _fallback_tags(card)

    return all_tags


def _fallback_tags(card: dict) -> dict:
    """Generate basic fallback tags when AI classification fails."""
    type_line = card.get("type_line", "")
    is_land = "Land" in type_line
    is_creature = "Creature" in type_line
    is_permanent = any(t in type_line for t in ["Creature", "Enchantment", "Artifact", "Planeswalker"])

    tags = {
        "cast_cost": None if is_land else {"total": card.get("cmc", 0), "colors": {}},
        "is_land": is_land,
        "permanent": is_permanent or is_land,
        "enters_tapped": False,
        "mana_production": None,
        "on_resolve": [],
        "on_etb": [],
        "on_attack": [],
        "power": int(card["power"]) if card.get("power") and card["power"].isdigit() else None,
        "toughness": int(card["toughness"]) if card.get("toughness") and card["toughness"].isdigit() else None,
        "static_effects": [],
    }

    return tags