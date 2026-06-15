"""
AI Tag Classifier — maps user prompts to functional card categories.

Replaces hardcoded trigger word lists and oracle text pattern matching.
Uses a lightweight AI call (~1s) to understand natural language intent.
"""

import os
import json
from openai import OpenAI
from data.scryfall_tags import CATEGORY_TAG_GROUPS, ORACLE_FALLBACKS, AVAILABLE_CATEGORIES

_client = None

def _get_client():
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client


def classify_tags(prompt: str) -> dict:
    """
    Classify a user prompt into functional card categories.
    
    Returns:
        {
            "categories": ["ramp", "mana_rocks"],
            "is_specific": false,
            "raw_prompt": "suggest ramp"
        }
    
    is_specific=True means the prompt needs mechanical detail
    that tags alone can't capture (e.g., "equipment that grants trample")
    """
    client = _get_client()

    system = f"""You classify Magic: The Gathering card requests into functional categories.

Available categories:
{json.dumps(AVAILABLE_CATEGORIES)}

Respond with ONLY valid JSON:
{{"categories": ["category1"], "is_specific": false}}

Rules:
- Pick 1-3 categories that best match what the user wants
- is_specific = true ONLY for very narrow mechanical requests that need
  oracle text filtering (e.g., "equipment that grants trample to legendary creatures")
- For broad requests, is_specific = false
- If the prompt is a general deck request ("suggest cards", "what should I add"),
  return {{"categories": ["general"], "is_specific": false}}

Examples:
"suggest ramp" → {{"categories": ["ramp"], "is_specific": false}}
"mana rocks under $5" → {{"categories": ["mana_rocks"], "is_specific": false}}
"I need ways to protect my commander" → {{"categories": ["protection"], "is_specific": false}}
"cards that benefit from gaining life" → {{"categories": ["lifegain_payoff"], "is_specific": false}}
"board wipes" → {{"categories": ["board_wipe"], "is_specific": false}}
"sacrifice outlets for aristocrats" → {{"categories": ["sacrifice", "death_triggers"], "is_specific": false}}
"ways to draw cards" → {{"categories": ["draw"], "is_specific": false}}
"removal spells" → {{"categories": ["removal"], "is_specific": false}}
"counterspells" → {{"categories": ["counterspell"], "is_specific": false}}
"give my creatures haste" → {{"categories": ["haste_enabler"], "is_specific": false}}
"tutor effects" → {{"categories": ["tutor"], "is_specific": false}}
"equipment that grants trample" → {{"categories": ["evasion"], "is_specific": true}}
"creatures with ETB effects" → {{"categories": ["attack_triggers"], "is_specific": true}}
"suggest cards for this deck" → {{"categories": ["general"], "is_specific": false}}
"any more ramp I can add" → {{"categories": ["ramp"], "is_specific": false}}
"what should I cut" → NOT a suggest request, don't classify
"how does trample work" → NOT a suggest request, don't classify"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
            max_tokens=150,
            timeout=10,
        )
        content = response.choices[0].message.content.strip()
        content = content.replace("```json", "").replace("```", "").strip()
        result = json.loads(content)
        result["raw_prompt"] = prompt
        return result
    except Exception as e:
        print(f"[AI] Tag classifier failed: {e}")
        return {"categories": ["general"], "is_specific": False, "raw_prompt": prompt}


def filter_by_category(cards: list, categories: list) -> list:
    """
    Filter cards by category using tags + oracle fallback.
    
    Each card should have:
        - "tags": [list of tag strings] (from tag index)
        - "oracle_text": str (for fallback)
    
    Returns cards that match ANY of the requested categories.
    """
    if not categories or "general" in categories:
        return cards

    matches = []
    for card in cards:
        card_tags = card.get("tags", [])
        oracle_text = card.get("oracle_text", "")
        matched = False

        for cat in categories:
            # Tag match (high confidence)
            group = CATEGORY_TAG_GROUPS.get(cat, [])
            if group:
                card_tags_lower = [t.lower() for t in card_tags]
                if any(g.lower() in card_tags_lower for g in group):
                    card["_match_source"] = "tag"
                    card["_match_category"] = cat
                    matched = True
                    break

            # Oracle fallback (medium confidence)
            hints = ORACLE_FALLBACKS.get(cat, [])
            if hints and oracle_text:
                text_lower = oracle_text.lower()
                if any(h.lower() in text_lower for h in hints):
                    card["_match_source"] = "oracle"
                    card["_match_category"] = cat
                    matched = True
                    break

        if matched:
            matches.append(card)

    return matches