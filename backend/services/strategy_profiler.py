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
    card_names_for_rating = []
    for card in deck_cards:
        full_data = card_lookup.get(card.scryfall_id, {})
        oracle = full_data.get("oracle_text", "")[:150]
        type_line = full_data.get("type_line", "")
        mana_cost = full_data.get("mana_cost", "")
        cmc = full_data.get("cmc", 0)
        card_lines.append(
            f"- {card.quantity}x {card.card_name} | {type_line} | {mana_cost} (CMC {cmc}) | {oracle}"
        )
        if card.board != "commander":
            card_names_for_rating.append(card.card_name)

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
        profile = json.loads(content)

        # Generate impact ratings in a separate call
        impact_ratings = _generate_impact_ratings(
            deck_info=deck_info,
            card_names=card_names_for_rating,
            card_lines=card_lines,
            commander_text=commander_text,
            profile=profile,
            role_data=role_data,
            analytics=analytics,
        )
        if impact_ratings:
            profile["card_impact_ratings"] = impact_ratings

        return profile

    except Exception as e:
        return {"error": str(e)}


def _generate_impact_ratings(deck_info: dict, card_names: list,
                              card_lines: list, commander_text: str,
                              profile: dict, role_data: dict,
                              analytics: dict) -> list:
    """
    Generate per-card impact ratings in batches.
    Splits cards into groups to avoid token limits.
    """
    all_ratings = []

    # Build context summary (compact — reused across batches)
    identity = analytics.get("deck_identity", {})
    context = f"""Deck: {deck_info.get('name', 'Unknown')} | Format: {deck_info.get('format', 'Unknown')}
{commander_text}
Strategy: {profile.get('primary_strategy', 'Unknown')}
Win conditions: {json.dumps(profile.get('win_conditions', []))}
Critical cards: {json.dumps(profile.get('critical_cards', []))}
Deck identity: {identity.get('recommendation_weight', 'balanced')}
Average CMC: {analytics.get('average_cmc', 0)}
Primary creature type: {role_data.get('primary_creature_type', 'None')}"""

    system = """You are an expert Magic: The Gathering deck analyst.
Rate each card's strategic importance to THIS SPECIFIC DECK on a 1-10 scale.

Respond with ONLY a valid JSON array (no markdown, no backticks):
[
    {"card_name": "Card Name", "score": 8, "reason": "One sentence explaining the rating"},
    ...
]

SCORING GUIDE:
9-10 CORE: Deck's strategy depends on this card. Removing it significantly weakens the game plan.
     Examples: key tribal payoffs, irreplaceable engines, best-in-class effects.
7-8  STRONG: High synergy, hard to replace. Does its job exceptionally well in this deck.
     Examples: draw engines that trigger off the deck's main activity, efficient fixing.
5-6  SOLID: Competent but replaceable. Works fine but a better option likely exists.
     Examples: generic removal, redundant ramp without specific synergy.
3-4  FLEXIBLE: Weaker option in its category. Could be upgraded or swapped.
     Examples: overcosted effects, generic utility with no commander synergy.
1-2  CUTTABLE: Lowest impact. Off-theme, redundant with better options, or too expensive.

KEY FACTORS:
1. SYNERGY with commander and deck strategy (most important)
2. UNIQUENESS — does anything else in the deck do this?
3. EFFICIENCY — CMC vs impact
4. ROLE COVERAGE — is this role over/under-represented?

IMPORTANT: Be honest — a well-built deck has a range. Roughly:
5-10 cards at 9-10, 15-20 at 7-8, 20-30 at 5-6, 5-15 at 3-4.
Rate ALL cards provided — do not skip any."""

    # Split into batches of 25
    batch_size = 25
    for i in range(0, len(card_names), batch_size):
        batch_names = card_names[i:i + batch_size]

        # Get the card lines for this batch
        batch_lines = []
        for name in batch_names:
            for line in card_lines:
                if name in line:
                    batch_lines.append(line)
                    break

        # Get role info for this batch
        role_lookup = {}
        if role_data:
            for cr in role_data.get("card_roles", []):
                role_lookup[cr["name"].lower()] = cr

        role_lines = []
        for name in batch_names:
            ri = role_lookup.get(name.lower(), {})
            primary = ri.get("primary_role", "unknown")
            secondary = ri.get("secondary_roles", [])
            synergy = ri.get("synergy_notes", "")
            role_str = f"  [{primary}]"
            if secondary:
                role_str += f" (also: {', '.join(secondary)})"
            if synergy:
                role_str += f" — {synergy}"
            role_lines.append(f"- {name}{role_str}")

        user_msg = f"""{context}

Rate these {len(batch_names)} cards:
{chr(10).join(batch_lines)}

Card roles:
{chr(10).join(role_lines)}"""

        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_msg},
                ],
                temperature=0.3,
                max_tokens=3000,
            )

            content = response.choices[0].message.content.strip()
            content = content.replace("```json", "").replace("```", "").strip()
            batch_ratings = json.loads(content)

            if isinstance(batch_ratings, list):
                all_ratings.extend(batch_ratings)

        except Exception as e:
            print(f"Impact rating batch {i // batch_size + 1} failed: {e}")
            continue

    # Deduplicate ratings (keep first occurrence)
    seen = set()
    deduped = []
    for rating in all_ratings:
        name = rating.get("card_name", "").lower()
        if name not in seen:
            seen.add(name)
            deduped.append(rating)

    return deduped