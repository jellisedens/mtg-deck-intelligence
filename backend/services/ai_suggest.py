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
from services.role_classifier import classify_deck_roles
from services.deck_context import build_deck_context, build_simulation_context
from services.cut_analyzer import build_cut_context
from data.mtg_glossary import GLOSSARY, CLARIFICATIONS, REPLACEMENT_GUIDE, SYNERGY_RULES, STRATEGIC_CONTEXT

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL = "gpt-4o-mini"


async def get_suggestions(prompt: str, deck_cards: list = None, deck_info: dict = None,
                          simulation_data: dict = None) -> dict:
    """
    Main entry point for AI suggestions.
    """
    clarification = _check_for_clarification(prompt)
    if clarification:
        return clarification

    deck_context = None
    analytics = None
    role_data = None
    card_lookup = None
    if deck_cards:
        analytics = await compute_analytics(deck_cards, include_card_data=True)
        card_lookup = analytics.pop("_card_lookup", {})
        role_data = classify_deck_roles(deck_cards, card_lookup, deck_info)
        deck_context = build_deck_context(deck_cards, deck_info, analytics, card_lookup, role_data)

    plan = _get_ai_plan(prompt, deck_context)

    if "error" in plan:
        return plan

    existing_cards = set()
    if deck_cards:
        for card in deck_cards:
            existing_cards.add(card.card_name.lower())

    search_results = await _execute_searches(
        queries=plan.get("scryfall_queries", []),
        exclude_cards=existing_cards,
    )

    if len(search_results) < 20:
        broader_plan = _get_broader_queries(prompt, plan, deck_context)
        if broader_plan and broader_plan.get("scryfall_queries"):
            additional_results = await _execute_searches(
                queries=broader_plan.get("scryfall_queries", []),
                exclude_cards=existing_cards,
            )
            seen_ids = {r["scryfall_id"] for r in search_results}
            for result in additional_results:
                if result["scryfall_id"] not in seen_ids:
                    search_results.append(result)
                    seen_ids.add(result["scryfall_id"])
            search_results.sort(key=lambda c: c.get("edhrec_rank") or 999999)

    recommendations = _get_ai_recommendations(
        prompt=prompt,
        plan=plan,
        search_results=search_results,
        deck_context=deck_context,
        role_data=role_data,
        deck_info=deck_info,
        simulation_data=simulation_data,
        card_lookup=card_lookup,
        deck_cards=deck_cards,
    )

    recommendations["debug"] = {
        "mode": plan.get("mode"),
        "reasoning": plan.get("reasoning"),
        "scryfall_queries": plan.get("scryfall_queries", []),
        "total_search_results": len(search_results),
        "simulation_informed": simulation_data is not None,
    }

    if role_data:
        recommendations["debug"]["role_distribution"] = role_data.get("role_distribution", {})
        recommendations["debug"]["primary_creature_type"] = role_data.get("primary_creature_type")

    return recommendations


def _check_for_clarification(prompt: str) -> dict | None:
    """Check if the prompt needs clarification before searching."""
    prompt_lower = prompt.lower().strip()

    for term, config in CLARIFICATIONS.items():
        term_words = term.split()

        is_broad = (
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


def _get_broader_queries(prompt: str, original_plan: dict, deck_context: str = None) -> dict:
    """When initial queries return too few results, generate broader queries."""
    system = """You are a Scryfall query expert. The previous search returned fewer than 20 results.
Generate 2-3 BROADER queries that cover the same strategic intent but cast a wider net.

Rules:
- Remove price filters (usd<X) from queries
- Remove CMC restrictions or widen them
- Use fewer combined search terms per query
- Think about the STRATEGIC ROLE, not exact mechanics
- Always include f:commander

Respond with ONLY valid JSON:
{
    "scryfall_queries": ["query1", "query2"]
}"""

    user_msg = f"""Original request: {prompt}
Original queries that returned too few results: {json.dumps(original_plan.get('scryfall_queries', []))}
Original reasoning: {original_plan.get('reasoning', '')}"""

    if deck_context:
        if is_cut_focused:
            # For cut requests, truncate deck context to save tokens
            context_lines = deck_context.split("\n")
            # Keep strategy profile and analytics, trim individual card oracle text
            trimmed_context = "\n".join(line for line in context_lines
                                        if not line.strip().startswith("Text:"))
            user_msg += f"\nDeck context:\n{trimmed_context}"
        else:
            user_msg += f"\nDeck context:\n{deck_context}"

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
    except Exception:
        return None


def _get_ai_plan(prompt: str, deck_context: str = None) -> dict:
    """Ask AI to interpret the request and create a search plan."""
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

{REPLACEMENT_GUIDE}

LOW RESULTS SAFEGUARD:
Always generate at least 3-4 queries to ensure sufficient results.
If your queries are very specific, also include 1-2 broader fallback queries.
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

    all_results.sort(key=lambda c: c.get("edhrec_rank") or 999999)
    return all_results


def _get_ai_recommendations(prompt: str, plan: dict, search_results: list,
                            deck_context: str = None, role_data: dict = None,
                            deck_info: dict = None, simulation_data: dict = None,
                            card_lookup: dict = None, deck_cards: list = None) -> dict:
    """Ask AI to analyze Scryfall results and give final recommendations."""
    max_results = plan.get("max_results", 10)

    system = f"""You are an expert Magic: The Gathering deck building advisor.
Analyze the search results and provide recommendations based on the user's request.

You must respond with ONLY valid JSON (no markdown, no backticks) in this format:
{{
    "summary": "Start with a 1-2 sentence strategic analysis of the deck (citing specific numbers from analytics), then overview your recommendations",
    "suggestions": [
        {{
            "card_name": "Card Name",
            "scryfall_id": "the-scryfall-uuid",
            "reasoning": "Why this card is good — reference specific synergies with existing cards",
            "category": "ramp/removal/draw/creature/land/utility/etc",
            "priority": "high/medium/low",
            "budget_note": "$X.XX" or null
        }}
    ],
    "cuts": [
        {{
            "card_name": "Card name from CUT CANDIDATES list",
            "reasoning": "Why this is cuttable — cite its impact score and what the deck loses"
        }}
    ],
    "strategy_notes": "Overall strategic advice for the deck"
}}

Rules:
- Only suggest cards that appear in the search results provided
- Include the exact scryfall_id from the search results
- Order suggestions by priority (best first)
- Cards are sorted by EDHREC popularity (most-played first) — prefer cards near the top
- All cards already in the user's deck have been pre-filtered out
- NEVER suggest a card that does not have a matching scryfall_id in the search results
- If the user has a deck, suggest cuts only when relevant
- Include price info when the user mentions budget
- Be specific about WHY each card is good, referencing synergies with existing cards by name
- Provide a MIX of card types when the concept spans multiple categories
- When deck analytics are provided, ALWAYS reference specific numbers in your summary
- Start your summary with a brief deck diagnosis when analytics are available
- MANA COST OPTIMIZATION:
  - If average CMC is above 3.5, prefer lower-cost suggestions
  - When two cards fill the same role, prefer lower CMC unless the expensive one is significantly better
  - For a deck with average CMC 4+, prioritize cards with CMC 3 or less for non-creature roles
- MATCH SUGGESTIONS TO DECK IDENTITY:
  - If permanent-heavy: suggest creature-based draw, ramp creatures, removal on bodies
  - If spell-heavy: suggest cantrips, spell-based engines, instant/sorcery cost reducers
  - NEVER suggest spellslinger cards for permanent-heavy decks or vice versa
- UNDERSTAND THE DIFFERENCE between ramp and color fixing:
  - When the user asks for "color fixing," do NOT suggest colorless-only mana sources
- SIMULATION-INFORMED DECISIONS:
  When SIMULATION PERFORMANCE DATA is provided, use actual performance numbers:
  - If mana_on_curve_rate < 70% on turn 3: never suggest cutting ramp
  - If a color has < 60% access by turn 5: prioritize fixing for it
  - If avg_uncastable_cards > 3 by turn 5: suggest lower CMC cards
  - ALWAYS cite specific simulation numbers in your reasoning
  - Cross-reference simulation data with cut decisions

{SYNERGY_RULES}

{STRATEGIC_CONTEXT}

USING IMPACT RATINGS FOR CUTS:
If CARD IMPACT RATINGS are provided, they are authoritative for cut decisions:
- ONLY suggest cutting cards rated 1-6 from the CUT CANDIDATES list
- NEVER suggest cutting cards rated 7-10 (STRONG/CORE)
- Always cite the impact score in your cut reasoning
- If simulation shows a category is struggling, do NOT cut cards in that category
- If all candidates score 5+, the deck is well-optimized — still suggest the lowest-scoring cards but warn about the tradeoff
- Suggest 2-3 cuts when asked. If only 1 card is clearly cuttable, include the next-lowest scoring cards and note they are harder to cut.
- When the user asks to "make room for" or "add more" of something, ALSO populate the suggestions array with matching cards from search results. Do NOT return empty suggestions when search results exist.
"""

    # Detect request type for context sizing
    add_keywords = ["make room for", "add more", "swap in", "fit in", "include more"]
    wants_additions = any(kw in prompt.lower() for kw in add_keywords)
    is_cut_focused = "cut" in prompt.lower() and not wants_additions

    # Trim search results — cut-only requests need fewer results
    if is_cut_focused:
        trimmed_results = search_results[:15]
    else:
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

    # Add simulation performance data
    if simulation_data:
        sim_context = build_simulation_context(simulation_data)
        if sim_context:
            user_msg += f"\n{sim_context}"

    # Add cut candidates from impact ratings
    if deck_info and deck_context and "cut" in prompt.lower():
        cut_context = build_cut_context(
            deck_info=deck_info,
            simulation_data=simulation_data,
            deck_cards=deck_cards,
            card_lookup=card_lookup,
        )
        if cut_context:
            user_msg += f"\n\n{cut_context}"
            print(f"CUT CONTEXT ADDED: {cut_context[:500]}")
        else:
            print("CUT CONTEXT: empty or None")
    else:
        print(f"CUT BLOCK SKIPPED: deck_info={bool(deck_info)}, deck_context={bool(deck_context)}, cut_in_prompt={'cut' in prompt.lower()}")
        


    # Build final instruction based on request type

    if wants_additions and "cut" in prompt.lower():
        user_msg += f"\n\nIMPORTANT — TWO-PART RESPONSE REQUIRED:"
        user_msg += f"\n1. CUTS: You MUST suggest exactly 2-3 cards from the CUT CANDIDATES list above. Do NOT return an empty cuts array."
        user_msg += f"\n2. SUGGESTIONS: You MUST suggest {max_results} cards from the search results. Do NOT return an empty suggestions array."
        user_msg += f"\nBoth arrays being empty is WRONG. Fill both."
    elif "cut" in prompt.lower():
        user_msg += f"\n\nYou MUST suggest exactly 2-3 cards from the CUT CANDIDATES list above. Do NOT return an empty cuts array."
        user_msg += f"\nAlso provide {max_results} suggestions if search results are available."
    else:
        user_msg += f"\n\nProvide {max_results} suggestions (use the full amount, do not be conservative)."

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

        # Enrich suggestions — verify both ID and name match
        result_lookup = {c["scryfall_id"]: c for c in search_results}
        name_lookup = {c["name"].lower(): c for c in search_results}
        verified_suggestions = []
        for suggestion in result.get("suggestions", []):
            card_data = result_lookup.get(suggestion.get("scryfall_id"))
            suggested_name = suggestion.get("card_name", "").lower()

            if card_data and card_data.get("name", "").lower() == suggested_name:
                suggestion["image_uri"] = card_data.get("image_uris", {}).get("normal", "")
                suggestion["mana_cost"] = card_data.get("mana_cost", "")
                suggestion["type_line"] = card_data.get("type_line", "")
                suggestion["price_usd"] = card_data.get("prices", {}).get("usd")
                verified_suggestions.append(suggestion)
            elif suggested_name in name_lookup:
                correct_data = name_lookup[suggested_name]
                suggestion["scryfall_id"] = correct_data["scryfall_id"]
                suggestion["image_uri"] = correct_data.get("image_uris", {}).get("normal", "")
                suggestion["mana_cost"] = correct_data.get("mana_cost", "")
                suggestion["type_line"] = correct_data.get("type_line", "")
                suggestion["price_usd"] = correct_data.get("prices", {}).get("usd")
                verified_suggestions.append(suggestion)

        result["suggestions"] = verified_suggestions

        # Post-process cuts
        if role_data:
            primary_type = (role_data.get("primary_creature_type") or "").lower()
            role_list = role_data.get("card_roles", [])
            role_by_name = {cr["name"].lower(): cr for cr in role_list}
            deck_card_names = {cr["name"].lower() for cr in role_list}

            critical_cards = set()
            if deck_info and isinstance(deck_info, dict):
                profile = deck_info.get("strategy_profile") or {}
                for card_name in profile.get("critical_cards", []):
                    critical_cards.add(card_name.lower())

                # Also block cards scored 8+ from cuts
                impact_ratings = profile.get("card_impact_ratings", [])
                for rating in impact_ratings:
                    if rating.get("score", 0) >= 8:
                        critical_cards.add(rating["card_name"].lower())

            verified_cuts = []
            for cut in result.get("cuts", []):
                cut_name = cut.get("card_name", "").lower()

                if cut_name not in deck_card_names:
                    continue
                if cut_name in critical_cards:
                    continue

                is_protected = False
                if primary_type and primary_type in cut_name:
                    is_protected = True

                cr = role_by_name.get(cut_name, {})
                if cr.get("primary_role") == "tribal_synergy":
                    is_protected = True
                if "tribal_synergy" in cr.get("secondary_roles", []):
                    is_protected = True

                if not is_protected:
                    verified_cuts.append(cut)

            result["cuts"] = verified_cuts

        return result

    except json.JSONDecodeError as e:
        return {"error": "ai_parse_error", "details": f"Failed to parse AI response: {str(e)}"}
    except Exception as e:
        return {"error": "ai_error", "details": str(e)}