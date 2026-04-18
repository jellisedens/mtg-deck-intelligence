"""
AI-powered strategy profile generator.
Analyzes a deck and generates a structured strategic profile
that can be stored and referenced for all future AI interactions.
"""

import os
import json
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL = "gpt-4o-mini"


def generate_strategy_profile(deck_info: dict, deck_cards: list,
                               card_lookup: dict, analytics: dict,
                               role_data: dict) -> dict:
    """
    Generate a comprehensive strategy profile for a deck.

    Returns a structured dict that gets stored in deck.strategy_profile.
    """
    # Build card summary with oracle text
    card_lines = []
    for card in deck_cards:
        full_data = card_lookup.get(card.scryfall_id, {})
        oracle = full_data.get("oracle_text", "")[:150]
        type_line = full_data.get("type_line", "")
        card_lines.append(f"- {card.quantity}x {card.card_name} | {type_line} | {oracle}")

    # Get commander info
    commander_cards = [c for c in deck_cards if c.board == "commander"]
    commander_text = ""
    if commander_cards:
        cmd = commander_cards[0]
        cmd_data = card_lookup.get(cmd.scryfall_id, {})
        commander_text = f"""Commander: {cmd.card_name}
Type: {cmd_data.get('type_line', '')}
Mana Cost: {cmd_data.get('mana_cost', '')}
CMC: {cmd_data.get('cmc', 0)}
Abilities: {cmd_data.get('oracle_text', '')}"""

    primary_type = role_data.get("primary_creature_type", "None")
    role_dist = role_data.get("role_distribution", {})
    identity = analytics.get("deck_identity", {})

    system = """You are an expert Magic: The Gathering deck analyst. Analyze this Commander deck
and generate a comprehensive strategic profile.

Respond with ONLY valid JSON (no markdown, no backticks):
{
    "commander_role": "What the commander does and how it should be used",
    "primary_strategy": "The deck's main game plan in 2-3 sentences",
    "win_conditions": ["list of specific ways this deck wins games"],
    "key_synergies": [
        {
            "cards": ["Card A", "Card B"],
            "description": "How these cards work together"
        }
    ],
    "critical_cards": ["cards that are essential to the strategy and should never be cut"],
    "weaknesses": ["identified weaknesses in the deck"],
    "ideal_curve": "Description of what the ideal early/mid/late game looks like",
    "role_needs": {
        "needs_more": ["roles that are under-represented"],
        "has_enough": ["roles that are well-covered"],
        "over_saturated": ["roles with too many cards"]
    },
    "cut_guidance": "General advice on what types of cards could be cut without hurting the strategy",
    "upgrade_priorities": ["ordered list of what to improve first"]
}"""

    user_msg = f"""Deck: {deck_info.get('name', 'Unknown')}
Format: {deck_info.get('format', 'Unknown')}
Description: {deck_info.get('description', 'None provided')}

{commander_text}

Primary creature type: {primary_type}
Average CMC: {analytics.get('average_cmc', 0)}
Total cards: {analytics.get('total_cards', 0)}
Deck identity: {identity.get('recommendation_weight', 'balanced')}
Spells: {identity.get('spell_count', 0)} | Permanents: {identity.get('permanent_count', 0)}

Role distribution:
{json.dumps(role_dist, indent=2)}

Mana curve: {json.dumps(analytics.get('mana_curve', {}))}
Color distribution: {json.dumps({c: info['count'] for c, info in analytics.get('color_distribution', {}).items() if info['count'] > 0})}
Mana base: {json.dumps(analytics.get('mana_base', {}))}

Card list:
{chr(10).join(card_lines)}"""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.3,
        )

        content = response.choices[0].message.content.strip()
        content = content.replace("```json", "").replace("```", "").strip()
        return json.loads(content)

    except Exception as e:
        return {"error": str(e)}