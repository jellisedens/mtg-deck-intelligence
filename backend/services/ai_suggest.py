"""
AI suggestion engine.
Handles two modes:
  1. Smart Search — translates natural language to Scryfall queries
  2. Deck Advisor — analyzes deck context and gives targeted advice
"""

import os
import json
from openai import OpenAI
from services.scryfall import scryfall_service
from services.analytics import compute_analytics
from data.mtg_glossary import GLOSSARY, CLARIFICATIONS

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL = "gpt-4o-mini"


async def get_suggestions(prompt: str, deck_cards: list = None, deck_info: dict = None) -> dict:
    """
    Main entry point for AI suggestions.

    Args:
        prompt: User's natural language request
        deck_cards: Optional list of DeckCard ORM objects for deck context
        deck_info: Optional dict with deck name, format, description
    """
    # Check if the prompt matches a broad term that needs clarification
    clarification = _check_for_clarification(prompt)
    if clarification:
        return clarification
    # Build deck context if we have cards
    deck_context = None
    analytics = None
    if deck_cards:
        analytics = await compute_analytics(deck_cards)
        deck_context = _build_deck_context(deck_cards, deck_info, analytics)

    # Step 1: Ask AI to interpret the request and build a plan
    plan = _get_ai_plan(prompt, deck_context)

    if "error" in plan:
        return plan

    # Step 2: Execute Scryfall searches from the plan
    # Build set of existing card names for duplicate filtering
    existing_cards = set()
    if deck_cards:
        for card in deck_cards:
            existing_cards.add(card.card_name.lower())

    search_results = await _execute_searches(
        queries=plan.get("scryfall_queries", []),
        exclude_cards=existing_cards,
    )

    # Step 3: Ask AI to analyze results and give final recommendations
    recommendations = _get_ai_recommendations(
        prompt=prompt,
        plan=plan,
        search_results=search_results,
        deck_context=deck_context,
    )

    # Include debug info about what was queried
    recommendations["debug"] = {
        "mode": plan.get("mode"),
        "reasoning": plan.get("reasoning"),
        "scryfall_queries": plan.get("scryfall_queries", []),
        "total_search_results": len(search_results),
    }

    return recommendations

def _check_for_clarification(prompt: str) -> dict | None:
    """
    Check if the user's prompt is a broad term that would benefit
    from clarification before searching.
    Returns a clarification response or None if no clarification needed.
    """
    prompt_lower = prompt.lower().strip()

    for term, config in CLARIFICATIONS.items():
        # Check if the prompt is essentially just the broad term
        # with minimal qualifiers. If they've already been specific
        # (e.g., "cheap mana rocks under $2"), skip clarification.
        term_words = term.split()

        # Simple heuristic: if the prompt is short and contains the term,
        # it's probably broad enough to clarify
        is_broad = (
            # Direct match or very short prompt containing the term
            prompt_lower == term
            or prompt_lower in [f"{term} cards", f"find {term}", f"suggest {term}",
                                f"recommend {term}", f"show me {term}", f"list {term}",
                                f"i need {term}", f"need {term}", f"what {term}",
                                f"best {term}", f"good {term}"]
            or (
                all(w in prompt_lower for w in term_words)
                and len(prompt_lower.split()) <= 8
                and not any(qualifier in prompt_lower for qualifier in [
                    "under", "below", "cheap", "budget", "expensive",
                    "best", "creature", "artifact", "instant", "sorcery",
                    "enchantment", "land", "dork", "rock", "spell",
                    "board wipe", "spot", "counter", "engine", "draw",
                    "specific", "exactly", "only", "just",
                ])
            )
        )

        if is_broad:
            return {
                "needs_clarification": True,
                "clarification_question": config["display"],
                "clarification_options": config["options"],
                "summary": None,
                "suggestions": [],
                "cuts": [],
                "strategy_notes": None,
            }

    return None

def _build_deck_context(deck_cards: list, deck_info: dict, analytics: dict) -> str:
    """Build a text summary of the deck for the AI prompt."""
    lines = []

    if deck_info:
        lines.append(f"Deck: {deck_info.get('name', 'Unknown')}")
        lines.append(f"Format: {deck_info.get('format', 'Unknown')}")
        if deck_info.get("description"):
            lines.append(f"Strategy: {deck_info['description']}")

    lines.append(f"\nTotal cards: {analytics.get('total_cards', 0)}")
    lines.append(f"Average CMC: {analytics.get('average_cmc', 0)}")

    # Card list
    lines.append("\nCurrent deck list:")
    for card in deck_cards:
        lines.append(f"  {card.quantity}x {card.card_name} ({card.board})")

    # Mana curve
    curve = analytics.get("mana_curve", {})
    lines.append(f"\nMana curve: {json.dumps(curve)}")

    # Color distribution
    colors = analytics.get("color_distribution", {})
    color_summary = {c: info["count"] for c, info in colors.items() if info["count"] > 0}
    lines.append(f"Color symbols in mana costs: {json.dumps(color_summary)}")

    # Type distribution
    types = analytics.get("type_distribution", {})
    type_summary = {t: c for t, c in types.items() if c > 0}
    lines.append(f"Card types: {json.dumps(type_summary)}")

    # Mana base
    mana_base = analytics.get("mana_base", {})
    lines.append(f"Lands: {mana_base.get('land_count', 0)} ({mana_base.get('land_percentage', 0)}%)")
    lines.append(f"Color sources: {json.dumps(mana_base.get('color_sources', {}))}")

    return "\n".join(lines)


def _get_ai_plan(prompt: str, deck_context: str = None) -> dict:
    """
    Ask AI to interpret the user's request and create a plan.
    Returns Scryfall queries to execute and the approach to take.
    """
    system = f"""You are an expert Magic: The Gathering deck building advisor.
Your job is to interpret the user's request and create a plan to help them.

You must respond with ONLY valid JSON (no markdown, no backticks) in this format:
{{
    "mode": "search" or "advisor",
    "reasoning": "brief explanation of your approach",
    "scryfall_queries": ["query1", "query2"],
    "needs_deck_context": true/false,
    "max_results": 10
}}

{GLOSSARY}

Scryfall query syntax reminders:
- Colors: c:red, c:UG, c<=WUB, id<=WUBRG (color identity for commander)
- Types: type:creature, t:instant, t:legendary
- CMC: cmc:3, cmc<=2, cmc>=5
- Oracle text: o:draw, o:"deal damage", o:goad
- Format: f:commander, f:modern, f:standard
- Rarity: r:mythic, r:rare
- Price: usd<1, usd<=5
- Power/toughness: pow>=5, tou<=2
- Keywords: keyword:flying, keyword:trample
- Combine with spaces (AND): c:red t:creature cmc<=3
- Use OR only within parentheses: (t:instant or t:sorcery)
- is:commander — cards that can be commanders

When building queries:
- For commander format, use id<= (color identity) instead of c: (card color)
- Use multiple queries to cover different subcategories of what the user wants
- Keep queries focused — 2-4 specific queries is better than 1 broad one
- Set max_results based on the request: 5-10 for specific advice, 20-50 for broad lists
- Always include format legality (f:commander) when the deck format is known

CRITICAL — MULTI-QUERY COVERAGE:
When a concept has multiple subcategories in the glossary (e.g., "ramp" includes mana dorks,
mana rocks, land search spells, and cost reducers), you MUST generate at least one query per
subcategory. This ensures the user gets a balanced mix of options, not just one type of card.
For example, "ramp" should produce 3-4 queries covering different ramp strategies.
"""

    user_msg = f"User request: {prompt}"
    if deck_context:
        user_msg += f"\n\nDeck context:\n{deck_context}"

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
        # Clean up potential markdown formatting
        content = content.replace("```json", "").replace("```", "").strip()
        return json.loads(content)

    except json.JSONDecodeError as e:
        return {"error": "ai_parse_error", "details": f"Failed to parse AI response: {str(e)}"}
    except Exception as e:
        return {"error": "ai_error", "details": str(e)}


async def _execute_searches(queries: list, exclude_cards: set = None) -> list:
    """Execute Scryfall searches, filter duplicates, and sort by EDHREC rank."""
    all_results = []
    seen_ids = set()
    exclude = exclude_cards or set()

    for query in queries:
        result = await scryfall_service.search_cards_raw(query)

        if "error" in result:
            continue

        cards = result.get("data", [])
        for card in cards:
            card_id = card["id"]
            card_name = card.get("name", "").lower()

            # Skip duplicates and cards already in the deck
            if card_id in seen_ids:
                continue
            if card_name in exclude:
                continue

            seen_ids.add(card_id)
            all_results.append({
                "name": card.get("name"),
                "mana_cost": card.get("mana_cost", ""),
                "cmc": card.get("cmc", 0),
                "type_line": card.get("type_line", ""),
                "oracle_text": card.get("oracle_text", ""),
                "colors": card.get("colors", []),
                "color_identity": card.get("color_identity", []),
                "rarity": card.get("rarity", ""),
                "prices": card.get("prices", {}),
                "image_uris": card.get("image_uris", {}),
                "scryfall_id": card_id,
                "edhrec_rank": card.get("edhrec_rank"),
                "power": card.get("power"),
                "toughness": card.get("toughness"),
                "keywords": card.get("keywords", []),
            })

    # Sort by EDHREC rank — lower rank = more popular in Commander
    # Cards without a rank go to the end
    all_results.sort(key=lambda c: c.get("edhrec_rank") or 999999)

    return all_results


def _get_ai_recommendations(prompt: str, plan: dict, search_results: list, deck_context: str = None) -> dict:
    """
    Ask AI to analyze Scryfall results and give final recommendations.
    """
    max_results = plan.get("max_results", 10)

    system = """You are an expert Magic: The Gathering deck building advisor.
Analyze the search results and provide recommendations based on the user's request.

You must respond with ONLY valid JSON (no markdown, no backticks) in this format:
{
    "summary": "If deck context is available, start with a 1-2 sentence diagnosis of the deck's current state (citing specific numbers), then overview your recommendations",
    "suggestions": [
        {
            "card_name": "Card Name",
            "scryfall_id": "the-scryfall-uuid",
            "reasoning": "Why this card is good for the request",
            "category": "ramp/removal/draw/creature/land/utility/etc",
            "priority": "high/medium/low",
            "budget_note": "$X.XX" or null
        }
    ],
    "cuts": [
        {
            "card_name": "Card to consider removing",
            "reasoning": "Why this card could be replaced"
        }
    ],
    "strategy_notes": "Any overall advice about the deck or strategy"
}

Rules:
- Only suggest cards that appear in the search results provided
- Include the exact scryfall_id from the search results
- Order suggestions by priority (best first)
- Cards are sorted by EDHREC popularity (most-played first) — prefer cards near the top of the list as they are proven staples
- All cards already in the user's deck have been pre-filtered out — do not worry about duplicates
- NEVER suggest a card that does not have a matching scryfall_id in the search results — if a card has no search result data, do not include it
- If the user has a deck, suggest cuts only when relevant
- Include price info when the user mentions budget
- Be specific about WHY each card is good, referencing synergies with existing cards
- Provide a MIX of card types when the concept spans multiple categories (e.g., ramp = mana dorks + mana rocks + land search spells)
- When deck analytics are provided, ALWAYS reference specific numbers in your summary and reasoning:
- Mana base: cite land count, land percentage, and color source counts
- Color distribution: identify which colors are over/under-represented
- Mana curve: note if the curve is too high or too low and suggest accordingly
- Type distribution: flag if there are too few creatures, too little interaction, etc.
- Example: "Your deck has 34 lands (34%) with only 8 white sources for 13 white pips — you need more white-producing mana rocks"
- Start your summary with a brief deck diagnosis when analytics are available, then lead into recommendations
- UNDERSTAND THE DIFFERENCE between ramp and color fixing:
  - Ramp = any card that accelerates mana production (colorless mana rocks count)
  - Color fixing = cards that produce COLORED mana, specifically colors the deck needs
  - When the user asks for "color fixing" or "mana fixing," do NOT suggest cards that only produce colorless mana (e.g., Mind Stone, Thought Vessel, Basalt Monolith, Everflowing Chalice)
  - When recommending color fixing, prioritize cards that produce ANY color (e.g., Chromatic Lantern, Arcane Signet, Commander's Sphere) or multiple specific colors
  - Reference the deck's color source gaps: if white has fewer sources than other colors, prioritize rocks that produce white
"""

    # Trim search results to avoid token limits
    trimmed_results = search_results[:80]

    user_msg = f"User request: {prompt}\n\n"
    user_msg += f"AI plan: {json.dumps(plan)}\n\n"
    user_msg += f"Search results ({len(trimmed_results)} cards found):\n"

    for card in trimmed_results:
        price = card.get("prices", {}).get("usd", "N/A")
        user_msg += f"- {card['name']} | {card['mana_cost']} | {card['type_line']} | ${price} | ID: {card['scryfall_id']}\n"
        if card.get("oracle_text"):
            user_msg += f"  Text: {card['oracle_text'][:150]}\n"

    if deck_context:
        user_msg += f"\nDeck context:\n{deck_context}"

    user_msg += f"\n\nProvide up to {max_results} suggestions."

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.5,
        )

        content = response.choices[0].message.content.strip()
        content = content.replace("```json", "").replace("```", "").strip()
        result = json.loads(content)

        # Enrich suggestions with image data from search results
        result_lookup = {c["scryfall_id"]: c for c in search_results}
        verified_suggestions = []
        for suggestion in result.get("suggestions", []):
            card_data = result_lookup.get(suggestion.get("scryfall_id"))
            if card_data:
                suggestion["image_uri"] = card_data.get("image_uris", {}).get("normal", "")
                suggestion["mana_cost"] = card_data.get("mana_cost", "")
                suggestion["type_line"] = card_data.get("type_line", "")
                suggestion["price_usd"] = card_data.get("prices", {}).get("usd")
                verified_suggestions.append(suggestion)
            # Cards not found in search results are silently dropped

        result["suggestions"] = verified_suggestions

        return result

    except json.JSONDecodeError as e:
        return {"error": "ai_parse_error", "details": f"Failed to parse AI response: {str(e)}"}
    except Exception as e:
        return {"error": "ai_error", "details": str(e)}