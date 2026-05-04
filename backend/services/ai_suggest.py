"""
AI suggestion engine.
Routes user prompts through intent classification to specialized prompt builders.
"""

import os
import json
import time
import asyncio
import logging
from openai import OpenAI
from services.scryfall import scryfall_service
from services.analytics import compute_analytics
from services.role_classifier import classify_deck_roles
from services.deck_context import build_deck_context
from services.intent_router import classify_intent, INTENT_SUGGEST, INTENT_CUTS, INTENT_ANALYZE, INTENT_SWAP
from services.prompt_builders import (
    build_suggest_prompt, build_cuts_prompt,
    build_analyze_prompt, build_swap_prompt,
)
from data.mtg_glossary import GLOSSARY, CLARIFICATIONS, REPLACEMENT_GUIDE, SYNERGY_RULES, STRATEGIC_CONTEXT

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL = "gpt-4o-mini"

logger = logging.getLogger(__name__)


async def get_suggestions(prompt: str, deck_cards: list = None, deck_info: dict = None,
                          simulation_data: dict = None, card_lookup: dict = None) -> dict:
    """
    Main entry point for AI suggestions.
    Classifies intent and routes to the appropriate prompt builder.
    """
    t_start = time.time()

    # Check for clarification needs
    clarification = _check_for_clarification(prompt)
    if clarification:
        return clarification

    # Classify intent
    intent_result = classify_intent(prompt, has_deck=deck_cards is not None)
    intent = intent_result["intent"]
    print(f"[AI] Intent: {intent} ({time.time() - t_start:.1f}s)")

    print(f"[AI] card_lookup provided: {card_lookup is not None}, cards: {len(card_lookup) if card_lookup else 0}")
    # Build deck context data (needed for most intents)
    t_ctx = time.time()
    analytics = None
    role_data = None
    if deck_cards:
        if card_lookup:
            t_qa = time.time()
            analytics = _build_quick_analytics(deck_cards, card_lookup)
            print(f"[AI] Quick analytics ({time.time() - t_qa:.1f}s)")
        else:
            t_ca = time.time()
            analytics = await compute_analytics(deck_cards, include_card_data=True)
            card_lookup = analytics.pop("_card_lookup", {})
            print(f"[AI] Full analytics ({time.time() - t_ca:.1f}s)")
        t_roles = time.time()
        # Use cached role data from strategy profile if available
        profile = (deck_info or {}).get("strategy_profile") or {}
        cached_roles = profile.get("role_data")
        if cached_roles:
            role_data = cached_roles
            print(f"[AI] Role classification (cached) ({time.time() - t_roles:.1f}s)")
        else:
            role_data = classify_deck_roles(deck_cards, card_lookup, deck_info)
            print(f"[AI] Role classification (computed) ({time.time() - t_roles:.1f}s)")
    print(f"[AI] Context built ({time.time() - t_ctx:.1f}s)")

    # Route based on intent
    t_route = time.time()
    if intent == INTENT_CUTS:
        result = await _handle_cuts(prompt, deck_info, simulation_data, deck_cards, card_lookup)
    elif intent == INTENT_ANALYZE:
        result = await _handle_analyze(prompt, deck_info, simulation_data)
    elif intent == INTENT_SWAP:
        result = await _handle_swap(
            prompt, deck_cards, deck_info, simulation_data,
            card_lookup, role_data, analytics,
        )
    else:
        result = await _handle_suggest(
            prompt, deck_cards, deck_info, simulation_data,
            card_lookup, role_data, analytics,
        )
    print(f"[AI] Handler complete ({time.time() - t_route:.1f}s)")
    print(f"[AI] Total: {time.time() - t_start:.1f}s")

    # Add debug info
    result.setdefault("debug", {})
    result["debug"]["intent"] = intent
    result["debug"]["intent_confidence"] = intent_result["confidence"]
    result["debug"]["intent_method"] = intent_result["method"]
    result["debug"]["simulation_informed"] = simulation_data is not None
    result["debug"]["total_time_seconds"] = round(time.time() - t_start, 1)

    if role_data:
        result["debug"]["role_distribution"] = role_data.get("role_distribution", {})
        result["debug"]["primary_creature_type"] = role_data.get("primary_creature_type")

    return result


async def _handle_suggest(prompt: str, deck_cards: list, deck_info: dict,
                          simulation_data: dict, card_lookup: dict,
                          role_data: dict, analytics: dict) -> dict:
    """Handle card suggestion requests."""
    # Build search plan
    t_plan = time.time()
    deck_context = None
    if deck_cards:
        deck_context = build_deck_context(deck_cards, deck_info, analytics, card_lookup, role_data)

    plan = _get_ai_plan(prompt, deck_context)
    if "error" in plan:
        return plan
    print(f"[AI] Search plan ({time.time() - t_plan:.1f}s)")

    # Execute searches
    existing_cards = set()
    if deck_cards:
        for card in deck_cards:
            existing_cards.add(card.card_name.lower())

    t_search = time.time()
    search_results = await _execute_searches(
        queries=plan.get("scryfall_queries", []),
        exclude_cards=existing_cards,
    )
    print(f"[AI] Search results: {len(search_results)} ({time.time() - t_search:.1f}s)")

    if len(search_results) < 5:
        t_broaden = time.time()
        search_results = await _broaden_search(prompt, plan, deck_context, search_results, existing_cards)
        print(f"[AI] Broadened to {len(search_results)} ({time.time() - t_broaden:.1f}s)")

    # Build focused prompt
    trimmed_results = search_results[:30]
    system, user_msg = build_suggest_prompt(
        prompt=prompt,
        plan=plan,
        search_results=trimmed_results,
        deck_info=deck_info,
        simulation_data=simulation_data,
        synergy_rules=SYNERGY_RULES,
        strategic_context=STRATEGIC_CONTEXT,
    )

    # Call AI and process
    t_ai = time.time()
    result = _call_ai(system, user_msg)
    print(f"[AI] Main AI call ({time.time() - t_ai:.1f}s)")

    result = _verify_suggestions(result, search_results)
    result.setdefault("debug", {})
    result["debug"]["scryfall_queries"] = plan.get("scryfall_queries", [])
    result["debug"]["total_search_results"] = len(search_results)

    return result


async def _handle_cuts(prompt: str, deck_info: dict, simulation_data: dict,
                       deck_cards: list, card_lookup: dict) -> dict:
    """Handle cut recommendation requests."""
    t_ai = time.time()
    system, user_msg = build_cuts_prompt(
        prompt=prompt,
        deck_info=deck_info,
        simulation_data=simulation_data,
        deck_cards=deck_cards,
        card_lookup=card_lookup,
    )

    result = _call_ai(system, user_msg)
    print(f"[AI] Cuts AI call ({time.time() - t_ai:.1f}s)")

    result = _verify_cuts(result, deck_info)
    result.setdefault("suggestions", [])
    result.setdefault("debug", {})

    return result


async def _handle_analyze(prompt: str, deck_info: dict, simulation_data: dict) -> dict:
    """Handle deck analysis requests."""
    t_ai = time.time()
    system, user_msg = build_analyze_prompt(
        prompt=prompt,
        deck_info=deck_info,
        simulation_data=simulation_data,
    )

    result = _call_ai(system, user_msg)
    print(f"[AI] Analyze AI call ({time.time() - t_ai:.1f}s)")

    # Force empty arrays — analysis puts everything in strategy_notes
    result["suggestions"] = []
    result["cuts"] = []
    result.setdefault("debug", {})

    return result


async def _handle_swap(prompt: str, deck_cards: list, deck_info: dict,
                       simulation_data: dict, card_lookup: dict,
                       role_data: dict, analytics: dict) -> dict:
    """Handle swap requests (cut + replace)."""
    t_plan = time.time()
    deck_context = None
    if deck_cards:
        deck_context = build_deck_context(deck_cards, deck_info, analytics, card_lookup, role_data)

    plan = _get_ai_plan(prompt, deck_context)
    if "error" in plan:
        return plan
    print(f"[AI] Swap plan ({time.time() - t_plan:.1f}s)")

    existing_cards = set()
    if deck_cards:
        for card in deck_cards:
            existing_cards.add(card.card_name.lower())

    t_search = time.time()
    search_results = await _execute_searches(
        queries=plan.get("scryfall_queries", []),
        exclude_cards=existing_cards,
    )
    print(f"[AI] Swap search: {len(search_results)} ({time.time() - t_search:.1f}s)")

    if len(search_results) < 5:
        search_results = await _broaden_search(prompt, plan, deck_context, search_results, existing_cards)

    system, user_msg = build_swap_prompt(
        prompt=prompt,
        plan=plan,
        search_results=search_results[:30],
        deck_info=deck_info,
        simulation_data=simulation_data,
        deck_cards=deck_cards,
        card_lookup=card_lookup,
        synergy_rules=SYNERGY_RULES,
        strategic_context=STRATEGIC_CONTEXT,
    )

    t_ai = time.time()
    result = _call_ai(system, user_msg)
    print(f"[AI] Swap AI call ({time.time() - t_ai:.1f}s)")

    result = _verify_suggestions(result, search_results)
    result = _verify_cuts(result, deck_info)
    result.setdefault("debug", {})
    result["debug"]["scryfall_queries"] = plan.get("scryfall_queries", [])
    result["debug"]["total_search_results"] = len(search_results)

    return result


# === SHARED UTILITIES ===

def _call_ai(system: str, user_msg: str) -> dict:
    """Make an AI call and parse JSON response."""
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
        return json.loads(content)
    except json.JSONDecodeError as e:
        return {"error": "ai_parse_error", "details": f"Failed to parse AI response: {str(e)}"}
    except Exception as e:
        return {"error": "ai_error", "details": str(e)}


def _verify_suggestions(result: dict, search_results: list) -> dict:
    """Verify suggested cards exist in search results."""
    if "error" in result:
        return result

    result_lookup = {c["scryfall_id"]: c for c in search_results}
    name_lookup = {c["name"].lower(): c for c in search_results}
    verified = []

    for suggestion in result.get("suggestions", []):
        card_data = result_lookup.get(suggestion.get("scryfall_id"))
        suggested_name = suggestion.get("card_name", "").lower()

        if card_data and card_data.get("name", "").lower() == suggested_name:
            suggestion["image_uri"] = card_data.get("image_uris", {}).get("normal", "")
            suggestion["mana_cost"] = card_data.get("mana_cost", "")
            suggestion["type_line"] = card_data.get("type_line", "")
            suggestion["price_usd"] = card_data.get("prices", {}).get("usd")
            verified.append(suggestion)
        elif suggested_name in name_lookup:
            correct_data = name_lookup[suggested_name]
            suggestion["scryfall_id"] = correct_data["scryfall_id"]
            suggestion["image_uri"] = correct_data.get("image_uris", {}).get("normal", "")
            suggestion["mana_cost"] = correct_data.get("mana_cost", "")
            suggestion["type_line"] = correct_data.get("type_line", "")
            suggestion["price_usd"] = correct_data.get("prices", {}).get("usd")
            verified.append(suggestion)

    result["suggestions"] = verified
    return result


def _verify_cuts(result: dict, deck_info: dict) -> dict:
    """Verify cuts are valid — not critical cards, not high-impact."""
    if "error" in result:
        return result

    profile = (deck_info or {}).get("strategy_profile") or {}

    # Build protected set
    critical_cards = set()
    for card_name in profile.get("critical_cards", []):
        critical_cards.add(card_name.lower())
    for rating in profile.get("card_impact_ratings", []):
        if rating.get("score", 0) >= 8:
            critical_cards.add(rating["card_name"].lower())

    verified = []
    for cut in result.get("cuts", []):
        cut_name = cut.get("card_name", "").lower()
        if cut_name not in critical_cards:
            verified.append(cut)

    result["cuts"] = verified
    return result


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


def _get_ai_plan(prompt: str, deck_context: str = None) -> dict:
    """Ask AI to create a Scryfall search plan."""
    system = f"""You are an expert Magic: The Gathering deck building advisor.
Interpret the user's request and create a search plan.

Respond with ONLY valid JSON:
{{
    "mode": "search" or "advisor",
    "reasoning": "brief explanation",
    "scryfall_queries": ["query1", "query2"],
    "needs_deck_context": true/false,
    "max_results": 10
}}

{GLOSSARY}

{REPLACEMENT_GUIDE}

Query rules:
- For commander, use id<= (color identity) not c: (card color)
- Multiple focused queries > one broad query
- Always include f:commander when format is known
- Generate 3-4 queries minimum covering different subcategories
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

def _build_quick_analytics(deck_cards: list, card_lookup: dict) -> dict:
    """Build lightweight analytics from pre-fetched card data. No Scryfall calls."""
    from collections import defaultdict

    mana_curve = defaultdict(int)
    color_dist = defaultdict(int)
    type_dist = defaultdict(int)
    total_cmc = 0
    nonland_count = 0
    total_cards = 0

    for deck_card in deck_cards:
        card_data = card_lookup.get(deck_card.scryfall_id, {})
        qty = deck_card.quantity
        total_cards += qty

        type_line = card_data.get("type_line", "")
        cmc = card_data.get("cmc", 0)

        # Type distribution
        for t in ["Creature", "Instant", "Sorcery", "Enchantment", "Artifact", "Planeswalker", "Land"]:
            if t in type_line:
                type_dist[t] += qty

        # Mana curve (nonlands only)
        if "Land" not in type_line:
            bucket = str(min(int(cmc), 7)) if int(cmc) < 7 else "7+"
            mana_curve[bucket] += qty
            total_cmc += cmc * qty
            nonland_count += qty

        # Color distribution
        for symbol in card_data.get("mana_cost", ""):
            if symbol in "WUBRG":
                color_dist[symbol] += qty

    color_names = {"W": "White", "U": "Blue", "B": "Black", "R": "Red", "G": "Green"}

    return {
        "total_cards": total_cards,
        "mana_curve": dict(mana_curve),
        "type_distribution": dict(type_dist),
        "color_distribution": {c: {"name": color_names.get(c, c), "count": v} for c, v in color_dist.items()},
        "average_cmc": round(total_cmc / nonland_count, 2) if nonland_count > 0 else 0,
    }

async def _execute_searches(queries: list, exclude_cards: set = None) -> list:
    """Execute Scryfall searches in parallel, filter duplicates, sort by EDHREC rank."""
    exclude = exclude_cards or set()

    # Run all queries concurrently
    t_start = time.time()
    tasks = [scryfall_service.search_cards_raw(q) for q in queries]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    print(f"[AI] Scryfall searches ({len(queries)} queries) took {time.time() - t_start:.1f}s")

    all_results = []
    seen_ids = set()

    for result in results:
        if isinstance(result, Exception):
            continue
        if "error" in result:
            continue

        for card in result.get("data", []):
            card_id = card["id"]
            card_name = card.get("name", "").lower()

            if card_id in seen_ids or card_name in exclude:
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


async def _broaden_search(prompt: str, plan: dict, deck_context: str,
                          search_results: list, exclude_cards: set) -> list:
    """Broaden search when initial results are too few."""
    system = """You are a Scryfall query expert. Previous search returned < 5 results.
Generate 2-3 BROADER queries. Remove price/CMC filters, use fewer terms.
Respond with ONLY valid JSON: {"scryfall_queries": ["query1", "query2"]}"""

    user_msg = f"Original request: {prompt}\nOriginal queries: {json.dumps(plan.get('scryfall_queries', []))}"
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
        content = response.choices[0].message.content.strip().replace("```json", "").replace("```", "").strip()
        broader_plan = json.loads(content)

        additional = await _execute_searches(
            queries=broader_plan.get("scryfall_queries", []),
            exclude_cards=exclude_cards,
        )
        seen_ids = {r["scryfall_id"] for r in search_results}
        for r in additional:
            if r["scryfall_id"] not in seen_ids:
                search_results.append(r)
                seen_ids.add(r["scryfall_id"])
        search_results.sort(key=lambda c: c.get("edhrec_rank") or 999999)
    except Exception:
        pass

    return search_results