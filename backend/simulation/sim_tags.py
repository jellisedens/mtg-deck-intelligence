"""
AI-powered simulation tag generator with knowledge base reference
and post-processing validation.
"""

import os
import json
from openai import OpenAI
from data.sim_tag_patterns import SIM_TAG_PATTERNS

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL = "gpt-4o-mini"


def generate_sim_tags(deck_cards: list, card_lookup: dict) -> dict:
    """
    Generate simulation tags for each card in the deck.
    Uses a knowledge base of patterns for accuracy and
    post-processes results to fix common mistakes.
    """
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

    json_format = """
Respond with ONLY valid JSON (no markdown, no backticks). Use this structure:
{
    "cards": [
        {
            "name": "Card Name",
            "sim_tags": {
                "cast_cost": {"total": 3, "colors": {"G": 1}} or null for lands,
                "is_land": false,
                "permanent": true,
                "enters_tapped": false,
                "mana_production": null or {
                    "type": "tap",
                    "produces": {"R": 1} or null,
                    "produces_choice": ["R", "G"] or null,
                    "produces_any": false,
                    "amount": 1
                },
                "on_resolve": [],
                "on_etb": [],
                "on_attack": [],
                "power": 5 or null,
                "toughness": 5 or null,
                "static_effects": []
            }
        }
    ]
}

AVAILABLE ACTIONS for on_resolve, on_etb, on_attack:
- {"action": "draw", "count": N}
- {"action": "put_back", "count": N, "destination": "top_of_library"}
- {"action": "search_land", "count": N, "destination": "battlefield" or "hand", "enters_tapped": true/false, "land_type": "basic" or "forest" or "any"}
- {"action": "shuffle_library"}
- {"action": "create_token", "count": N, "token": {"type": "Treasure"} or {"type": "Creature", "power": N, "toughness": N}}
- {"action": "add_mana", "mana": {"R": 1, "G": 1}}
- {"action": "destroy", "target": "creature" or "all_non_type"}
- {"action": "exile", "target": "creature" or "any"}
- {"action": "scry", "count": N}
- {"action": "deal_damage", "amount": N, "target": "any"}

AVAILABLE STATIC EFFECTS:
- {"effect": "cost_reduction", "applies_to": "dragon" or "creature" or "all", "amount": 1}
- {"effect": "haste", "applies_to": "dragon" or "creature"}
- {"effect": "draw_on_creature_etb", "condition": "power_3_or_greater" or "power_4_or_greater" or "any"}
- {"effect": "draw_on_combat_damage"}
- {"effect": "damage_on_creature_etb", "damage_source": "entering_creature_power"}
- {"effect": "token_on_dragon_etb", "token": {"type": "Creature", "power": 5, "toughness": 5}}
- {"effect": "lands_produce_any_color"}
- {"effect": "additional_land_drop", "count": 1}
- {"effect": "mana_doubling"}
"""

    rules = """
RULES:
- cast_cost is null for lands
- is_land is true only for Land type cards
- permanent is true for creatures, enchantments, artifacts, planeswalkers, AND lands
- permanent is false for instants and sorceries
- For dual lands that produce ONE color at a time: use produces_choice, NOT produces
- For shock lands: enters_tapped is FALSE (assume pay 2 life)
- For check lands (need 2 basics): enters_tapped is TRUE
- For basic lands: produces the matching color
- Eminence abilities work from command zone — always include as static_effect
- power/toughness: include for creatures, null for non-creatures
- ALWAYS reference the pattern knowledge base above before generating tags
"""

    system = (
        "You are a Magic: The Gathering rules engine. For each card, generate structured "
        "simulation tags that describe its mechanical effects in a format a game simulator can execute.\n\n"
        "REFERENCE THESE PATTERNS — they are authoritative and override your general knowledge:\n\n"
        + SIM_TAG_PATTERNS + "\n\n"
        + json_format + "\n\n"
        + rules
    )

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
                tags = card_data.get("sim_tags", {})
                # Find the original card summary for validation
                original = next((c for c in batch if c["name"].lower() == name), None)
                if original:
                    tags = _validate_and_fix(tags, original)
                all_tags[name] = tags

        except Exception as e:
            print(f"  Sim tag generation error: {type(e).__name__}: {e}")
            for card in batch:
                all_tags[card["name"].lower()] = _fallback_tags(card)

    return all_tags


def _validate_and_fix(tags: dict, card: dict) -> dict:
    """
    Post-processing validation to catch and fix common AI mistakes.
    """
    type_line = card.get("type_line", "")
    oracle = card.get("oracle_text", "").lower()
    name = card.get("name", "").lower()

    # Fix 1: Lands should always be permanent
    if "Land" in type_line:
        tags["is_land"] = True
        tags["permanent"] = True
        tags["cast_cost"] = None

    # Fix 2: Shock lands should enter untapped (assume pay life)
    shock_lands = [
        "stomping ground", "breeding pool", "blood crypt", "temple garden",
        "hallowed fountain", "godless shrine", "sacred foundry", "steam vents",
        "overgrown tomb", "watery grave"
    ]
    if name in shock_lands:
        tags["enters_tapped"] = False
        # Fix produces to produces_choice
        prod = tags.get("mana_production", {})
        if prod and prod.get("produces") and not prod.get("produces_choice"):
            colors = list(prod["produces"].keys())
            if len(colors) == 2:
                prod["produces"] = None
                prod["produces_choice"] = colors
                prod["produces_any"] = False

    # Fix 3: Check lands should enter tapped
    check_lands = [
        "cinder glade", "canopy vista", "prairie stream",
        "sunken hollow", "smoldering marsh"
    ]
    if name in check_lands:
        tags["enters_tapped"] = True
        prod = tags.get("mana_production", {})
        if prod and prod.get("produces") and not prod.get("produces_choice"):
            colors = list(prod["produces"].keys())
            if len(colors) == 2:
                prod["produces"] = None
                prod["produces_choice"] = colors

    # Fix 4: Dual lands should use produces_choice not produces
    if tags.get("is_land"):
        prod = tags.get("mana_production", {})
        if prod and prod.get("produces"):
            colors = [c for c in prod["produces"].keys() if c in ["W", "U", "B", "R", "G"]]
            if len(colors) == 2 and not prod.get("produces_any"):
                prod["produces"] = None
                prod["produces_choice"] = colors

    # Fix 5: Cultivate/Kodama's Reach — 1 to battlefield, 1 to hand
    if name in ["cultivate", "kodama's reach"]:
        tags["on_resolve"] = [
            {"action": "search_land", "count": 1, "destination": "battlefield",
             "enters_tapped": True, "land_type": "basic"},
            {"action": "search_land", "count": 1, "destination": "hand",
             "land_type": "basic"},
            {"action": "shuffle_library"}
        ]

    # Fix 6: Nature's Lore enters untapped
    if name == "nature's lore":
        tags["on_resolve"] = [
            {"action": "search_land", "count": 1, "destination": "battlefield",
             "enters_tapped": False, "land_type": "forest"},
            {"action": "shuffle_library"}
        ]

    # Fix 7: Farseek enters tapped
    if name == "farseek":
        tags["on_resolve"] = [
            {"action": "search_land", "count": 1, "destination": "battlefield",
             "enters_tapped": True, "land_type": "any_nonforest"},
            {"action": "shuffle_library"}
        ]

    # Fix 8: Creatures should have power/toughness
    if "Creature" in type_line:
        if card.get("power") and str(card["power"]).isdigit():
            tags["power"] = int(card["power"])
        if card.get("toughness") and str(card["toughness"]).isdigit():
            tags["toughness"] = int(card["toughness"])

    # Fix 9: Terror of the Peaks trigger
    if "whenever another creature enters" in oracle and "deals damage equal" in oracle:
        has_trigger = any(e.get("effect") == "damage_on_creature_etb"
                        for e in tags.get("static_effects", []))
        if not has_trigger:
            tags.setdefault("static_effects", []).append({
                "effect": "damage_on_creature_etb",
                "damage_source": "entering_creature_power"
            })

    # Fix 10: Draw on creature ETB triggers
    if "whenever a creature" in oracle and "power" in oracle and "draw" in oracle:
        has_trigger = any("draw" in e.get("effect", "")
                        for e in tags.get("static_effects", []))
        if not has_trigger:
            condition = "power_4_or_greater" if "4 or greater" in oracle else "power_3_or_greater"
            tags.setdefault("static_effects", []).append({
                "effect": "draw_on_creature_etb",
                "condition": condition
            })

    # Fix 11: Eminence should always be a static effect
    if "eminence" in oracle:
        has_eminence = any(e.get("effect") == "cost_reduction"
                         for e in tags.get("static_effects", []))
        if not has_eminence and "cost" in oracle and "less" in oracle:
            tags.setdefault("static_effects", []).append({
                "effect": "cost_reduction",
                "applies_to": "dragon",
                "amount": 1
            })

    # Fix 12: Haste granters
    if "haste" in oracle and ("creatures you control" in oracle or "dragon" in oracle):
        has_haste = any(e.get("effect") == "haste"
                       for e in tags.get("static_effects", []))
        if not has_haste:
            applies = "dragon" if "dragon" in oracle else "creature"
            tags.setdefault("static_effects", []).append({
                "effect": "haste",
                "applies_to": applies
            })

    # Fix 13: Any-color mana rocks
    if "any color" in oracle and not tags.get("is_land"):
        prod = tags.get("mana_production", {})
        if prod and not prod.get("produces_any"):
            prod["produces_any"] = True
            prod["produces"] = None
            prod["produces_choice"] = None

    return tags


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
        "power": int(card["power"]) if card.get("power") and str(card["power"]).isdigit() else None,
        "toughness": int(card["toughness"]) if card.get("toughness") and str(card["toughness"]).isdigit() else None,
        "static_effects": [],
    }

    return tags


def _call_sim_tag_batch(system: str, user_msg: str, batch: list) -> dict:
    """Execute a single sim tag batch. Thread-safe."""
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

        tags = {}
        for card_data in parsed.get("cards", []):
            name = card_data.get("name", "").lower()
            card_tags = card_data.get("sim_tags", {})
            original = next((c for c in batch if c["name"].lower() == name), None)
            if original:
                card_tags = _validate_and_fix(card_tags, original)
            tags[name] = card_tags
        return tags

    except Exception as e:
        print(f"Sim tag batch failed: {e}")
        result = {}
        for card in batch:
            result[card["name"].lower()] = _fallback_tags(card)
        return result