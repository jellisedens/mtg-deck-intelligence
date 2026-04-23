"""
Specialized prompt builders for each intent type.
Each builder creates a focused, compact prompt optimized for its task.
"""

import json
from services.deck_context import build_simulation_context
from services.cut_analyzer import build_cut_context


def build_suggest_prompt(prompt: str, plan: dict, search_results: list,
                         deck_info: dict = None, simulation_data: dict = None,
                         synergy_rules: str = "", strategic_context: str = "") -> tuple:
    """
    Build prompt for card suggestions. Heavy on search results, light on deck details.
    Returns (system_prompt, user_message).
    """
    deck_summary = _get_deck_summary(deck_info)

    system = f"""You are an expert Magic: The Gathering deck building advisor.
Analyze the search results and recommend the best cards for this deck.

Respond with ONLY valid JSON:
{{
    "summary": "1-2 sentence deck diagnosis with specific numbers, then overview recommendations",
    "suggestions": [
        {{
            "card_name": "Card Name",
            "scryfall_id": "the-scryfall-uuid",
            "reasoning": "Why this card is good — reference synergies with existing cards",
            "category": "ramp/removal/draw/creature/land/utility/etc",
            "priority": "high/medium/low",
            "budget_note": "$X.XX" or null
        }}
    ],
    "cuts": [],
    "strategy_notes": "Overall strategic advice"
}}

Rules:
- Only suggest cards from the search results with exact scryfall_id
- Order by priority (best first)
- Prefer cards with lower EDHREC rank (more popular = more proven)
- Reference specific synergies with cards already in the deck
- If deck is permanent-heavy, prefer creature-based draw/ramp/removal
- If deck is spell-heavy, prefer instant/sorcery-based options
- If average CMC > 3.5, prefer lower-cost suggestions
- If simulation data shows weak colors, prioritize fixing for those colors
- Cite specific numbers from the deck summary in your reasoning

{synergy_rules}
{strategic_context}"""

    max_results = plan.get("max_results", 10)
    user_msg = f"User request: {prompt}\n\n"

    if deck_summary:
        user_msg += f"Deck summary:\n{deck_summary}\n\n"

    if simulation_data:
        sim_context = build_simulation_context(simulation_data)
        if sim_context:
            user_msg += f"{sim_context}\n"

    user_msg += f"Search results ({len(search_results)} cards):\n"
    for card in search_results:
        price = card.get("prices", {}).get("usd", "N/A")
        user_msg += f"- {card['name']} | {card['mana_cost']} | {card['type_line']} | ${price} | ID: {card['scryfall_id']}\n"
        if card.get("oracle_text"):
            user_msg += f"  Text: {card['oracle_text'][:150]}\n"

    user_msg += f"\nProvide {max_results} suggestions."

    return system, user_msg


def build_cuts_prompt(prompt: str, deck_info: dict = None,
                      simulation_data: dict = None,
                      deck_cards: list = None,
                      card_lookup: dict = None) -> tuple:
    """
    Build prompt for cut recommendations. Heavy on impact scores, no search results.
    Returns (system_prompt, user_message).
    """
    deck_summary = _get_deck_summary(deck_info)

    system = """You are an expert Magic: The Gathering deck advisor specializing in deck optimization.
Your job is to identify the weakest cards in this deck based on their pre-computed impact scores.

Respond with ONLY valid JSON:
{
    "summary": "1-2 sentence deck health assessment citing simulation numbers, then explain your cut reasoning",
    "suggestions": [],
    "cuts": [
        {
            "card_name": "Card name from the CUT CANDIDATES list",
            "reasoning": "Why this is cuttable — cite impact score, role, and what the deck loses"
        }
    ],
    "strategy_notes": "What the deck gains by making these cuts and what to add instead"
}

Rules:
- You MUST suggest exactly 2-3 cuts from the CUT CANDIDATES list below
- Pick the LOWEST scoring cards first
- Cite the impact score for each cut
- If simulation shows a category is struggling (mana below 80%, draw below 8), do NOT cut cards in that category
- If all candidates score 5+, note the deck is well-optimized but still pick the lowest
- Explain what the deck loses with each cut and why it's acceptable
- Do NOT return an empty cuts array — this is your primary task"""

    user_msg = f"User request: {prompt}\n\n"

    if deck_summary:
        user_msg += f"Deck summary:\n{deck_summary}\n\n"

    if simulation_data:
        sim_context = build_simulation_context(simulation_data)
        if sim_context:
            user_msg += f"{sim_context}\n"

    # Add cut candidates
    cut_context = build_cut_context(
        deck_info=deck_info,
        simulation_data=simulation_data,
        deck_cards=deck_cards,
        card_lookup=card_lookup,
    )
    if cut_context:
        user_msg += f"\n{cut_context}"

    user_msg += "\n\nYou MUST pick 2-3 cards from the CUT CANDIDATES list. Do NOT return empty cuts."

    return system, user_msg


def build_analyze_prompt(prompt: str, deck_info: dict = None,
                         simulation_data: dict = None) -> tuple:
    """
    Build prompt for deck health analysis. Heavy on simulation data, no search results.
    Returns (system_prompt, user_message).
    """
    deck_summary = _get_deck_summary(deck_info)

    system = """You are an expert Magic: The Gathering deck analyst.
Evaluate this deck's performance using the simulation data and strategic profile.

Respond with ONLY valid JSON:
{
    "summary": "2-3 sentence overall deck health assessment with specific numbers",
    "suggestions": [],
    "cuts": [],
    "strategy_notes": "Detailed analysis covering: 1) Mana development and color access, 2) Curve and castability, 3) Board presence and threat deployment, 4) Role balance, 5) Top 3 priorities for improvement"
}

Rules:
- Cite specific simulation numbers (mana on curve %, color access %, uncastable cards)
- Compare role counts against minimum thresholds
- Identify the deck's biggest strengths and weaknesses
- Prioritize the top 3 things to fix
- Be specific — "add 2 more white sources" not "improve mana base"
- Reference the impact rating distribution to assess overall deck quality"""

    user_msg = f"User request: {prompt}\n\n"

    if deck_summary:
        user_msg += f"Deck summary:\n{deck_summary}\n\n"

    if simulation_data:
        sim_context = build_simulation_context(simulation_data)
        if sim_context:
            user_msg += f"{sim_context}\n"

    # Add impact distribution if available
    profile = (deck_info or {}).get("strategy_profile") or {}
    impact_ratings = profile.get("card_impact_ratings", [])
    if impact_ratings:
        scores = [r.get("score", 5) for r in impact_ratings]
        user_msg += f"\nImpact rating distribution: avg {round(sum(scores)/len(scores), 1)}, "
        user_msg += f"core(9-10): {len([s for s in scores if s >= 9])}, "
        user_msg += f"strong(7-8): {len([s for s in scores if 7 <= s <= 8])}, "
        user_msg += f"solid(5-6): {len([s for s in scores if 5 <= s <= 6])}, "
        user_msg += f"flexible(3-4): {len([s for s in scores if 3 <= s <= 4])}"

    user_msg += "\n\nProvide a comprehensive deck health analysis."

    return system, user_msg


def build_swap_prompt(prompt: str, plan: dict, search_results: list,
                      deck_info: dict = None, simulation_data: dict = None,
                      deck_cards: list = None, card_lookup: dict = None,
                      synergy_rules: str = "", strategic_context: str = "") -> tuple:
    """
    Build prompt for card swaps (cut + replace). Balanced between cuts and search results.
    Returns (system_prompt, user_message).
    """
    deck_summary = _get_deck_summary(deck_info)

    system = f"""You are an expert Magic: The Gathering deck advisor.
The user wants to swap cards — identify what to CUT and what to ADD as replacements.

Respond with ONLY valid JSON:
{{
    "summary": "1-2 sentence deck assessment, then explain swap strategy",
    "suggestions": [
        {{
            "card_name": "Card Name",
            "scryfall_id": "the-scryfall-uuid",
            "reasoning": "Why this card is a good addition — what it replaces and why it's better",
            "category": "ramp/removal/draw/creature/land/utility/etc",
            "priority": "high/medium/low",
            "budget_note": "$X.XX" or null
        }}
    ],
    "cuts": [
        {{
            "card_name": "Card to remove",
            "reasoning": "Why cut this — cite impact score, pair with a specific replacement"
        }}
    ],
    "strategy_notes": "Overall swap strategy and what the deck gains"
}}

Rules:
- You MUST suggest 2-3 cuts from the CUT CANDIDATES list
- You MUST suggest 2-3 cards to add from the search results
- Pair each cut with a replacement when possible — explain the upgrade
- Cite impact scores for cuts
- Only suggest adding cards that appear in search results with exact scryfall_id
- If simulation data shows weak areas, prioritize swaps that fix those areas

{synergy_rules}
{strategic_context}"""

    max_results = plan.get("max_results", 10)
    user_msg = f"User request: {prompt}\n\n"

    if deck_summary:
        user_msg += f"Deck summary:\n{deck_summary}\n\n"

    if simulation_data:
        sim_context = build_simulation_context(simulation_data)
        if sim_context:
            user_msg += f"{sim_context}\n"

    # Cut candidates
    cut_context = build_cut_context(
        deck_info=deck_info,
        simulation_data=simulation_data,
        deck_cards=deck_cards,
        card_lookup=card_lookup,
    )
    if cut_context:
        user_msg += f"\n{cut_context}\n"

    # Scoped search results (fewer than suggest — just need replacements)
    scoped_results = search_results[:30]
    user_msg += f"\nReplacement options ({len(scoped_results)} cards):\n"
    for card in scoped_results:
        price = card.get("prices", {}).get("usd", "N/A")
        user_msg += f"- {card['name']} | {card['mana_cost']} | {card['type_line']} | ${price} | ID: {card['scryfall_id']}\n"
        if card.get("oracle_text"):
            user_msg += f"  Text: {card['oracle_text'][:150]}\n"

    user_msg += f"\nSuggest 2-3 cuts paired with {max_results} replacement cards. Do NOT return empty arrays."

    return system, user_msg


def _get_deck_summary(deck_info: dict) -> str:
    """Get the pre-cached compact deck summary from the strategy profile."""
    if not deck_info:
        return ""
    profile = deck_info.get("strategy_profile") or {}
    return profile.get("deck_summary", "")