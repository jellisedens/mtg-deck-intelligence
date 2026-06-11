"""
AI suggestion engine.
Routes user prompts through intent classification to specialized prompt builders.
"""

import re
import os
import json
import time
import asyncio
import logging
from openai import OpenAI
from services.mtg_knowledge import build_knowledge_context, SCRYFALL_SYNTAX_GUIDE
from services.scryfall import scryfall_service
from services.vector_search import search_with_context
from services.edhrec import fetch_commander_profile, format_edhrec_context_for_prompt, get_synergy_cards
from services.analytics import compute_analytics
from services.role_classifier import classify_deck_roles
from services.deck_context import build_deck_context
from services.effect_clarifier import check_for_effect_clarification
from services.search_spec import generate_search_spec, apply_spec_filter
from services.prompt_constraints import extract_deterministic_constraints, apply_deterministic_constraints 
from services.intent_router import classify_intent, INTENT_SUGGEST, INTENT_CUTS, INTENT_ANALYZE, INTENT_SWAP, INTENT_DISCUSS
from services.prompt_builders import (
    build_suggest_prompt, build_cuts_prompt,
    build_analyze_prompt, build_swap_prompt,
)
from data.mtg_glossary import GLOSSARY, CLARIFICATIONS, REPLACEMENT_GUIDE, SYNERGY_RULES, STRATEGIC_CONTEXT

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL = "gpt-4o-mini"

logger = logging.getLogger(__name__)

def _get_deck_color_identity(deck_info: dict = None, deck_cards: list = None, card_lookup: dict = None) -> list:
    """Get deck's color identity from multiple sources (fallback chain)."""
    def _valid_ci(ci):
        """Color identity must be a list of WUBRG letters."""
        if not ci or not isinstance(ci, list):
            return False
        valid = {"W", "U", "B", "R", "G"}
        return any(c in valid for c in ci)

    if deck_info:
        prefs = deck_info.get("preferences") or {}
        ci = prefs.get("color_identity")
        if _valid_ci(ci):
            return ci
        profile = deck_info.get("strategy_profile") or {}
        ci = profile.get("color_identity")
        if _valid_ci(ci):
            return ci
        edhrec = profile.get("edhrec_profile", {})
        edhrec_ci = edhrec.get("color_identity")
        if _valid_ci(edhrec_ci):
            return edhrec_ci
    if deck_cards and card_lookup:
        for card in deck_cards:
            if card.board == "commander":
                card_data = card_lookup.get(card.scryfall_id, {})
                ci = card_data.get("color_identity")
                if _valid_ci(ci):
                    if deck_info:
                        prefs = deck_info.get("preferences") or {}
                        prefs["color_identity"] = ci
                        deck_info["preferences"] = prefs
                        _persist_color_identity(deck_info, ci)
                    return ci
    print(f"[CI] No valid color identity found")
    return []

def _persist_color_identity(deck_info: dict, color_identity: list):
    """Save color identity to deck preferences in database."""
    try:
        from database.session import SessionLocal
        from sqlalchemy import text
        import json
        db = SessionLocal()
        deck_name = deck_info.get("name")
        if deck_name:
            prefs = deck_info.get("preferences") or {}
            prefs["color_identity"] = color_identity
            db.execute(
                text("UPDATE decks SET preferences = :prefs WHERE name = :name"),
                {"prefs": json.dumps(prefs), "name": deck_name},
            )
            db.commit()
            print(f"[AI] Auto-saved color identity {color_identity} to deck preferences")
        db.close()
    except Exception as e:
        print(f"[AI] Failed to persist color identity: {e}")


def _filter_by_color_identity(results: list, deck_color_identity: list) -> list:
    """Hard post-filter: remove any card whose color identity isn't a subset of the deck's."""
    if not deck_color_identity:
        return results
    deck_ci = set(deck_color_identity)
    filtered = []
    removed = 0
    for card in results:
        card_ci = set(card.get("color_identity", []))
        if card_ci.issubset(deck_ci):
            filtered.append(card)
        else:
            removed += 1
    if removed > 0:
        print(f"[AI] Color identity filter removed {removed} illegal cards")
    return filtered


def _extract_requested_count(prompt: str) -> int | None:
    """Extract explicit count from prompt like 'suggest 10 cards' or 'show me all'."""
    prompt_lower = prompt.lower()
    count_match = re.search(r'\b(\d+)\s+\w+\s*(card|creature|spell|suggestion)', prompt_lower)
    if count_match:
        return min(int(count_match.group(1)), 20)
    if any(phrase in prompt_lower for phrase in ["all ", "every ", "as many as"]):
        return 20
    return None

def _expand_compact_suggestions(result: dict) -> dict:
    """Transform compact AI picks format into full suggestions format."""
    if "picks" not in result:
        return result  # Already in full format or error
    
    suggestions = []
    for pick in result.get("picks", []):
        if not isinstance(pick, list) or len(pick) < 2:
            continue
        card_name = pick[0] if len(pick) > 0 else ""
        scryfall_id = pick[1] if len(pick) > 1 else ""
        category = pick[2] if len(pick) > 2 else "utility"
        reasoning = pick[3] if len(pick) > 3 else ""
        
        suggestions.append({
            "card_name": card_name,
            "scryfall_id": scryfall_id,
            "reasoning": reasoning,
            "category": category,
            "priority": None,
            "budget_note": None,
        })
    
    result["suggestions"] = suggestions
    result.pop("picks", None)
    result.setdefault("cuts", [])
    return result

def _build_representative_sample(all_results: list, queries: list, max_cards: int) -> list:
    """
    Build a representative sample ensuring results from each query are included.
    Prevents niche/specific query results from being drowned by high-volume generic queries.
    Each query gets a fair share of slots, filled by EDHREC rank within that query's results.
    """
    if not queries or len(queries) <= 1:
        return all_results[:max_cards]
    
    # We don't track which result came from which query in the current flow,
    # so re-run a lightweight check: for each result, test which queries it likely matched
    # This is approximate but effective
    per_query_slots = max(2, max_cards // len(queries))
    selected = []
    seen_ids = set()
    
    # First pass: take top results from each query position
    # Since results are sorted by EDHREC rank globally, earlier results are more popular
    # We want to ensure later queries (often more specific) get representation
    
    # Split results into "early" (from broad queries, high volume) and "late" (from specific queries, low volume)
    # Heuristic: cards with very low EDHREC rank (<1000) are likely generic staples
    # Cards with higher EDHREC rank but still in results are likely from specific queries
    
    # Simpler approach: take top N by EDHREC, but also include some from the tail
    # that have characteristics matching the specific queries
    top_results = all_results[:max_cards]
    
    # Also grab cards from positions max_cards to max_cards*3 that might be specific query hits
    extended_pool = all_results[max_cards:] if len(all_results) > max_cards else []
    
    # Look for cards in the extended pool whose oracle text or type line 
    # contains terms from the later (more specific) queries
    if extended_pool and len(queries) >= 2:
        # Extract key terms from the last 2 queries (typically the most specific)
        specific_terms = set()
        for q in queries[:2]:  # first queries are now the specific ones (planner puts them first)
            for term in ["dragon", "elf", "goblin", "zombie", "angel", "demon", "vampire",
                         "wizard", "tribal", "otag"]:
                if term in q.lower():
                    specific_terms.add(term)
        
        if specific_terms:
            specific_hits = []
            for card in extended_pool:
                card_text = (card.get("oracle_text", "") + " " + card.get("type_line", "")).lower()
                if any(term in card_text for term in specific_terms):
                    specific_hits.append(card)
            
            # Replace some generic results with specific hits
            if specific_hits:
                # Keep top half from EDHREC ranking, replace bottom half with specific hits
                half = max_cards // 2
                top_half = top_results[:half]
                specific_portion = specific_hits[:max_cards - half]
                # Fill remaining with generic if needed
                remaining = max_cards - len(top_half) - len(specific_portion)
                generic_fill = top_results[half:half + remaining] if remaining > 0 else []
                return top_half + specific_portion + generic_fill
    
    return top_results


def _apply_playbook_filter(results: list, prompt: str, deck_info: dict) -> list:
    """Filter results based on playbook avoid guidance for the matched category."""
    if not deck_info:
        return results
    
    playbook = (deck_info.get("strategy_profile") or {}).get("archetype_playbook", {})
    if not playbook:
        return results
    
    prompt_lower = prompt.lower()
    category_keywords = {
        "ramp": ["ramp", "mana", "accelerat"],
        "card_draw": ["draw", "card advantage", "card draw"],
        "removal": ["removal", "remove", "destroy", "exile", "kill"],
        "protection": ["protect", "hexproof", "indestructible", "counter"],
    }
    
    matched_category = None
    for cat, keywords in category_keywords.items():
        if any(kw in prompt_lower for kw in keywords):
            matched_category = cat
            break
    
    if not matched_category:
        return results
    
    guidance = playbook.get("category_guidance", {}).get(matched_category, {})
    avoid_text = guidance.get("avoid", "").lower()
    
    if not avoid_text:
        return results
    
    avoid_types = set()
    if "creature" in avoid_text:
        avoid_types.add("Creature")
    if "enchantment" in avoid_text:
        avoid_types.add("Enchantment")
    if "sorcery" in avoid_text:
        avoid_types.add("Sorcery")
    if "instant" in avoid_text:
        avoid_types.add("Instant")
    if "artifact" in avoid_text:
        avoid_types.add("Artifact")
    
    if not avoid_types:
        return results
    
    filtered = []
    removed = []
    for card in results:
        type_line = card.get("type_line", "")
        should_remove = any(t in type_line for t in avoid_types)
        if should_remove:
            removed.append(card)
        else:
            filtered.append(card)
    
    # Keep at least half the results
    min_results = max(len(results) // 2, 8)
    if len(filtered) < min_results:
        filtered.extend(removed[:min_results - len(filtered)])
    
    return filtered

async def get_suggestions(prompt: str, deck_cards: list = None, deck_info: dict = None,
                          simulation_data: dict = None, card_lookup: dict = None,
                          conversation_context: list = None,
                          intent_override: str = None) -> dict:
    """
    Main entry point for AI suggestions.
    Classifies intent and routes to the appropriate prompt builder.
    """
    t_start = time.time()
    
    # Handle vague responses to clarification ("any", "all", "I don't know")
    vague_responses = [
        "any", "all", "all types", "everything", "any type",
        "i don't know", "i'm not sure", "im not sure", "not sure",
        "idk", "whatever", "surprise me", "all of them",
        "don't know", "no preference",
    ]
    if prompt.lower().strip() in vague_responses:
        prompt = "suggest cards for this deck"
        print(f"[AI] Vague clarification response detected, rewritten to: '{prompt}'")
    elif not intent_override:
        # Only clarify when user hasn't explicitly selected a mode
        clarification = _check_for_clarification(prompt)
        if clarification:
            print(f"[AI] Category clarifier caught: '{prompt}' -> {clarification.get('clarification_question')}")
            return clarification
        effect_clarification = check_for_effect_clarification(prompt)
        if effect_clarification:
            print(f"[AI] Effect clarifier caught: '{prompt}' -> {effect_clarification.get('clarification_question')}")
            return effect_clarification
        


    # Classify intent (skip if user explicitly selected a mode)
    if intent_override and intent_override in (INTENT_SUGGEST, INTENT_CUTS, INTENT_ANALYZE, INTENT_SWAP, INTENT_DISCUSS):
        intent = intent_override
        intent_result = {"intent": intent, "confidence": "override", "method": "user_selected"}
        print(f"[AI] Intent override: {intent}")
    else:
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
    elif intent == INTENT_DISCUSS:
        result = await _handle_discuss(prompt, deck_info)
    elif intent == INTENT_SWAP:
        result = await _handle_swap(
            prompt, deck_cards, deck_info, simulation_data,
            card_lookup, role_data, analytics,
        )
    else:
        result = await _handle_suggest(
            prompt, deck_cards, deck_info, simulation_data,
            card_lookup, role_data, analytics, conversation_context,
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

def _merge_vector_results(search_results: list, prompt: str, deck_info: dict, existing_cards: set) -> list:
    """Run vector search and merge results into existing Scryfall results."""
    t_vector = time.time()
    try:
        deck_colors = None
        deck_format = "commander"
        if deck_info:
            deck_colors = _get_deck_color_identity(deck_info)
            deck_format = deck_info.get("format", "commander")

        vector_results = search_with_context(
            query=prompt,
            deck_color_identity=deck_colors,
            deck_card_names=list(existing_cards),
            deck_format=deck_format,
            limit=15,
        )

        seen_names = {r["name"].lower() for r in search_results}
        vector_added = 0
        for vcard in vector_results.get("results", []):
            if vcard["name"].lower() not in seen_names:
                search_results.append({
                    "name": vcard["name"],
                    "mana_cost": vcard.get("mana_cost", ""),
                    "cmc": vcard.get("cmc", 0),
                    "type_line": vcard.get("type_line", ""),
                    "oracle_text": vcard.get("oracle_text", ""),
                    "colors": vcard.get("colors", []),
                    "color_identity": vcard.get("color_identity", []),
                    "rarity": vcard.get("rarity", ""),
                    "prices": vcard.get("prices", {}),
                    "image_uris": vcard.get("image_uris", {}),
                    "scryfall_id": vcard.get("scryfall_id", ""),
                    "edhrec_rank": vcard.get("edhrec_rank"),
                    "power": vcard.get("power"),
                    "toughness": vcard.get("toughness"),
                })
                seen_names.add(vcard["name"].lower())
                vector_added += 1

        search_results.sort(key=lambda c: c.get("edhrec_rank") or 999999)
        print(f"[AI] Vector search added {vector_added} new cards ({time.time() - t_vector:.1f}s)")
    except Exception as e:
        print(f"[AI] Vector search failed (non-fatal): {e}")
    
    return search_results

async def _handle_suggest(prompt: str, deck_cards: list, deck_info: dict,
                          simulation_data: dict, card_lookup: dict,
                          role_data: dict, analytics: dict,
                          conversation_context: list = None) -> dict:
    """Handle card suggestion requests."""
    t_plan = time.time()

    # Resolve color identity early so all downstream code has it
    deck_ci = _get_deck_color_identity(deck_info, deck_cards, card_lookup)
    if deck_ci and deck_info:
        prefs = deck_info.get("preferences") or {}
        if not prefs.get("color_identity"):
            prefs["color_identity"] = deck_ci
            deck_info["preferences"] = prefs
            print(f"[AI] Color identity resolved early: {deck_ci}")

    # Try direct query bypass first (skips AI calls for simple requests)
    plan = _try_direct_queries(prompt, deck_info)
    search_spec = None

    if plan:
        print(f"[AI] Direct bypass: {plan['reasoning']} ({time.time() - t_plan:.1f}s)")
        print(f"[AI] Queries: {plan.get('scryfall_queries', [])}")
        deck_context = None
    else:
        # Generate structured search spec (replaces AI planner)
        deck_ci = _get_deck_color_identity(deck_info, deck_cards, card_lookup)
        deck_format = (deck_info or {}).get("format", "commander")
        search_spec = generate_search_spec(prompt, color_identity=deck_ci, deck_format=deck_format)

        if search_spec.get("error") or not search_spec.get("scryfall_queries"):
            # Spec failed — fall back to AI planner
            deck_context = None
            if deck_cards:
                deck_context = build_deck_context(deck_cards, deck_info, analytics, card_lookup, role_data)
            plan = _get_ai_plan(prompt, deck_context, deck_info)
            if "error" in plan:
                return plan
            print(f"[AI] Fallback to AI planner ({time.time() - t_plan:.1f}s)")
        else:
            # Use spec as the plan
            plan = {
                "scryfall_queries": search_spec["scryfall_queries"],
                "max_results": search_spec.get("max_results", 8),
                "reasoning": search_spec.get("intent_summary", ""),
                "oracle_filters": search_spec.get("oracle_required", []),
                "mode": "search",
            }
            deck_context = None

        print(f"[AI] Queries: {plan.get('scryfall_queries', [])}")

    # Execute searches
    existing_cards = set()
    if deck_cards:
        for card in deck_cards:
            existing_cards.add(card.card_name.lower())

    # Fetch EDHREC commander profile (cached on deck)
    edhrec_profile = None
    commander_name = None
    if deck_cards:
        for card in deck_cards:
            if card.board == "commander":
                commander_name = card.card_name
                break
    if commander_name and deck_info:
        profile = deck_info.get("strategy_profile") or {}
        cached_edhrec = profile.get("edhrec_profile")
        
        # Use cached if exists and matches current commander
        if cached_edhrec and cached_edhrec.get("commander_name", "").lower() == commander_name.lower():
            edhrec_profile = cached_edhrec
            print(f"[AI] EDHREC profile (cached): {edhrec_profile['total_decks']} decks for {commander_name}")
        else:
            try:
                edhrec_profile = await fetch_commander_profile(commander_name)
                if edhrec_profile:
                    print(f"[AI] EDHREC profile fetched: {edhrec_profile['total_decks']} decks for {commander_name}")
                    # Cache on strategy profile
                    _cache_edhrec_profile(deck_info, edhrec_profile)
            except Exception as e:
                print(f"[AI] EDHREC fetch failed (non-fatal): {e}")

    # EDHREC-first: load commander-proven cards as primary source
    edhrec_cards_resolved = []
    if edhrec_profile:
        t_edhrec = time.time()
        all_edhrec = []
        for card in edhrec_profile.get("cards", []):
            name_lower = card["name"].lower()
            if name_lower in existing_cards:
                continue
            if card.get("inclusion_pct", 0) >= 20 or card.get("synergy", 0) >= 0.15:
                all_edhrec.append(card)

        if all_edhrec:
            identifiers = [{"name": c["name"]} for c in all_edhrec[:75]]
            resolved = await scryfall_service.get_collection(identifiers)
            if "data" in resolved:
                edhrec_lookup = {c["name"].lower(): c for c in all_edhrec}
                for card_data in resolved["data"]:
                    name_lower = card_data.get("name", "").lower()
                    ecard = edhrec_lookup.get(name_lower, {})
                    edhrec_cards_resolved.append({
                        "name": card_data.get("name", ""),
                        "mana_cost": card_data.get("mana_cost", ""),
                        "cmc": card_data.get("cmc", 0),
                        "type_line": card_data.get("type_line", ""),
                        "oracle_text": card_data.get("oracle_text", ""),
                        "colors": card_data.get("colors", []),
                        "color_identity": card_data.get("color_identity", []),
                        "rarity": card_data.get("rarity", ""),
                        "prices": card_data.get("prices", {}),
                        "image_uris": card_data.get("image_uris", {}),
                        "scryfall_id": card_data.get("id", ""),
                        "edhrec_rank": card_data.get("edhrec_rank"),
                        "power": card_data.get("power"),
                        "toughness": card_data.get("toughness"),
                        "keywords": card_data.get("keywords", []),
                        "_edhrec_proven": True,
                        "_edhrec_synergy": ecard.get("synergy", 0),
                        "_edhrec_inclusion_pct": ecard.get("inclusion_pct", 0),
                    })
                print(f"[AI] EDHREC-first: {len(edhrec_cards_resolved)} cards resolved ({time.time() - t_edhrec:.1f}s)")

    # If direct bypass matched a category, filter EDHREC to relevant cards only
    if edhrec_cards_resolved and plan.get("direct_bypass") and plan.get("reasoning"):
        category_oracle_hints = {
            "ramp": ["add {", "add one mana", "search your library for", "additional land", "mana of any", "treasure token", "cost", "less to cast"],
            "removal": ["destroy", "exile", "damage", "counter target"],
            "card draw": ["draw", "cards", "look at the top"],
            "protection": ["hexproof", "indestructible", "shroud", "protection from", "counter target"],
            "tokens": ["create", "token"],
        }
        for cat, hints in category_oracle_hints.items():
            if cat in plan.get("reasoning", "").lower():
                before = len(edhrec_cards_resolved)
                edhrec_cards_resolved = [
                    c for c in edhrec_cards_resolved
                    if any(h in (c.get("oracle_text") or "").lower() for h in hints)
                ]
                print(f"[AI] EDHREC category filter ({cat}): {before} -> {len(edhrec_cards_resolved)}")
                break

    # Scryfall search — fills gaps EDHREC doesn't cover
    t_search = time.time()
    search_results = await _execute_searches(
        queries=plan.get("scryfall_queries", []),
        exclude_cards=existing_cards,
    )
    print(f"[AI] Scryfall results: {len(search_results)} ({time.time() - t_search:.1f}s)")

    # Merge: EDHREC first, then Scryfall (deduplicated)
    seen_names = {c["name"].lower() for c in edhrec_cards_resolved}
    scryfall_unique = [c for c in search_results if c["name"].lower() not in seen_names]
    search_results = edhrec_cards_resolved + scryfall_unique
    print(f"[AI] Merged: {len(edhrec_cards_resolved)} EDHREC + {len(scryfall_unique)} Scryfall = {len(search_results)} total")

    # Vector search supplements
    search_results = _merge_vector_results(search_results, prompt, deck_info, existing_cards)

    if len(search_results) < 5:
        t_broaden = time.time()
        search_results = await _broaden_search(prompt, plan, deck_context, search_results, existing_cards)
        print(f"[AI] Broadened to {len(search_results)} ({time.time() - t_broaden:.1f}s)")

    # Hard color identity filter — catch anything that slipped through
    deck_ci = _get_deck_color_identity(deck_info, deck_cards, card_lookup)
    search_results = _filter_by_color_identity(search_results, deck_ci)

    # Deterministic constraints — CMC and price limits from prompt
    det_constraints = extract_deterministic_constraints(prompt)
    search_results = apply_deterministic_constraints(search_results, det_constraints)

    # Apply search spec filter (hard oracle enforcement) or fallback
    if search_spec:
        search_results = apply_spec_filter(search_results, search_spec)

    # Build focused prompt — scale results to requested count
    # Default to 5 unless user explicitly asked for more
    requested = _extract_requested_count(prompt)
    max_results = requested if requested else 8
    plan["max_results"] = max_results  # override planner's default of 10
    max_cards = min(max_results + 10, 30)  # give AI some extra options to choose from
    # Build a representative sample — take top results from EACH query
    # so specific/niche query results aren't drowned by generic ones
    trimmed_results = _build_representative_sample(search_results, plan.get("scryfall_queries", []), max_cards)
    
    # Apply playbook avoid filter
    trimmed_results = _apply_playbook_filter(trimmed_results, prompt, deck_info)
    
    # Slim card data for the AI prompt to reduce token count
    slim_results = []
    for card in trimmed_results:
        slim = {
            "name": card["name"],
            "mana_cost": card.get("mana_cost", ""),
            "cmc": card.get("cmc", 0),
            "type_line": card.get("type_line", ""),
            "oracle_text": card.get("oracle_text", ""),
            "rarity": card.get("rarity", ""),
            "scryfall_id": card["scryfall_id"],
            "edhrec_rank": card.get("edhrec_rank"),
        }
        if card.get("_edhrec_proven"):
            slim["edhrec_proven"] = True
            slim["edhrec_synergy"] = card.get("_edhrec_synergy", 0)
            slim["edhrec_inclusion_pct"] = card.get("_edhrec_inclusion_pct", 0)
        slim_results.append(slim)


    # Pass constraints to prompt builder
    if det_constraints:
        plan["_det_constraints"] = det_constraints

    # Inject EDHREC context for prompt builder
    if edhrec_profile and deck_info:
        deck_info["_edhrec_context"] = format_edhrec_context_for_prompt(
            edhrec_profile, list(existing_cards), max_cards=15
        )

        
    system, user_msg = build_suggest_prompt(
        prompt=prompt,
        plan=plan,
        search_results=slim_results,
        deck_info=deck_info,
        simulation_data=simulation_data,
        synergy_rules=SYNERGY_RULES,
        strategic_context=STRATEGIC_CONTEXT,
        conversation_context=conversation_context,
    )

    # Call AI and process
    print(f"[AI] Prompt size: system={len(system)} user={len(user_msg)} total={len(system)+len(user_msg)} chars (~{(len(system)+len(user_msg))//4} tokens)")
    t_ai = time.time()
    result = _call_ai(system, user_msg)
    print(f"[AI] Main AI call ({time.time() - t_ai:.1f}s)")

    result = _expand_compact_suggestions(result)
    result = _verify_suggestions(result, search_results)
    result.setdefault("debug", {})
    result["debug"]["scryfall_queries"] = plan.get("scryfall_queries", [])
    result["debug"]["total_search_results"] = len(search_results)
    result["debug"]["direct_bypass"] = plan.get("direct_bypass", False)

    return result

def _cache_edhrec_profile(deck_info: dict, edhrec_profile: dict):
    """Save EDHREC profile to the deck's strategy profile."""
    try:
        from database.session import SessionLocal
        from sqlalchemy import text
        import json

        profile = deck_info.get("strategy_profile") or {}
        profile["edhrec_profile"] = edhrec_profile
        deck_info["strategy_profile"] = profile

        # Persist to database if we have a deck reference
        db = SessionLocal()
        # Find deck by name from deck_info
        deck_name = deck_info.get("name")
        if deck_name:
            db.execute(
                text("UPDATE decks SET strategy_profile = :profile WHERE name = :name"),
                {"profile": json.dumps(profile), "name": deck_name},
            )
            db.commit()
        db.close()
    except Exception as e:
        print(f"[AI] Failed to cache EDHREC profile: {e}")
        
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

async def _handle_discuss(prompt: str, deck_info: dict = None) -> dict:
    """Handle strategy discussion questions — conversational MTG knowledge."""
    t_ai = time.time()

    deck_context = ""
    if deck_info:
        name = deck_info.get("name", "")
        fmt = deck_info.get("format", "commander")
        profile = deck_info.get("strategy_profile") or {}
        strategy = profile.get("primary_strategy", "")
        commander = profile.get("commander_name", "")
        if commander or name:
            deck_context = f"\nThe user's current deck: {name} ({fmt})"
            if commander:
                deck_context += f", commander: {commander}"
            if strategy:
                deck_context += f", strategy: {strategy}"
            deck_context += "\nReference their deck when relevant, but focus on answering the question."

    system = f"""You are an expert Magic: The Gathering strategy advisor with deep knowledge of 
all formats, mechanics, and deckbuilding theory.

The user is asking a strategy question — NOT requesting card suggestions or deck changes.
Give a thoughtful, conversational answer that teaches and informs.

Respond with ONLY valid JSON:
{{
    "summary": "Direct answer to their question in 2-3 sentences",
    "suggestions": [],
    "cuts": [],
    "strategy_notes": "Detailed explanation covering the topic. Include format-specific context, common misconceptions, and practical advice. Reference specific cards as examples where helpful, but don't turn this into a card suggestion list."
}}
{deck_context}"""

    result = _call_ai(system, prompt)
    print(f"[AI] Discuss AI call ({time.time() - t_ai:.1f}s)")

    result.setdefault("suggestions", [])
    result.setdefault("cuts", [])
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

    plan = _get_ai_plan(prompt, deck_context, deck_info)
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

    # Vector search — find conceptually similar cards
    search_results = _merge_vector_results(search_results, prompt, deck_info, existing_cards)

    if len(search_results) < 5:
        search_results = await _broaden_search(prompt, plan, deck_context, search_results, existing_cards)

    system, user_msg = build_swap_prompt(
        prompt=prompt,
        plan=plan,
        search_results=search_results[:20],
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
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # Try to fix common JSON issues
            # Remove trailing commas before ] or }
            content = re.sub(r',\s*([}\]])', r'\1', content)
            # Try again
            return json.loads(content)
    except json.JSONDecodeError as e:
        print(f"[AI] JSON parse failed. Raw content:\n{content[:500]}")
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
    """Check if the prompt needs clarification before searching.
    
    Only triggers for truly bare/vague prompts like just "ramp" or "removal".
    Does NOT trigger when the user includes action words like "suggest", "find",
    "recommend" etc. — those indicate the user knows what they want.
    """
    prompt_lower = prompt.lower().strip()
    
    # Never clarify if the user has an action word — they know what they want
    action_words = [
        "suggest", "find", "recommend", "show", "list", "give",
        "need", "want", "looking for", "search", "get me",
        "add", "include", "put in",
    ]
    has_action = any(word in prompt_lower for word in action_words)
    
    for term, config in CLARIFICATIONS.items():
        term_words = term.split()

        # Only trigger for bare terms with no action words and no qualifiers
        is_bare = (
            prompt_lower == term
            or prompt_lower in [f"{term} cards", f"best {term}", f"good {term}",
                                f"what {term}", f"{term}?"]
        )
        
        # Also trigger if it's short and vague (but NOT if it has an action word)
        is_vague = (
            not has_action
            and all(re.search(rf'\b{re.escape(w)}\b', prompt_lower) for w in term_words)
            and len(prompt_lower.split()) <= 4
            and not any(qualifier in prompt_lower for qualifier in [
                "under", "below", "cheap", "budget", "expensive",
                "creature", "artifact", "instant", "sorcery",
                "enchantment", "land", "dork", "rock", "spell",
                "board wipe", "spot", "counter", "engine",
                "specific", "exactly", "only", "just",
            ])
        )

        if is_bare or is_vague:
            return {
                "needs_clarification": True,
                "clarification_question": config["display"],
                "clarification_options": config["options"],
                "summary": None,
                "suggestions": [],
                "cuts": [],
                "strategy_notes": None,
                "_original_category": term,  # track what triggered clarification
            }

    return None

def _try_direct_queries(prompt: str, deck_info: dict = None) -> dict | None:
    """
    For common request patterns, build Scryfall queries directly
    without an AI call. Returns a plan dict if matched, None if
    AI planning is needed.
    
    This bypasses _get_ai_plan() (~15s) for common categories,
    bringing total suggest time from ~23s to ~8-10s.
    """
    prompt_lower = prompt.lower().strip()
    
    # Extract format and color identity from deck info
    fmt = "commander"  # default
    color_filter = ""
    
    if deck_info:
        fmt = deck_info.get("format", "commander") or "commander"
        colors = _get_deck_color_identity(deck_info)
        if colors:
            # Scryfall expects WUBRG order
            wubrg_order = "WUBRG"
            sorted_colors = "".join(c for c in wubrg_order if c in colors)
            color_filter = f" id<={sorted_colors}"
    
    format_filter = f" f:{fmt}"
    base = format_filter + color_filter
    
    # ── Pattern definitions ──────────────────────────────────
    # Each entry: list of trigger phrases → list of Scryfall queries
    # Queries use {base} placeholder for format + color filters
    
    PATTERNS = {
        "ramp": {
            "triggers": [
                "ramp", "mana rock", "mana rocks", "mana dork", "mana dorks",
                "acceleration", "mana acceleration", "ramp cards",
                "mana ramp", "more mana",
            ],
            "queries": [
                f"t:creature o:\"{{T}}: Add\"{base} cmc<=3",           # mana dorks
                f"t:artifact o:\"{{T}}: Add\"{base} cmc<=3",           # mana rocks
                f"o:\"search your library\" o:land t:sorcery{base}",   # land search
                f"o:\"additional land\"{base}",                         # extra land drops
                f"o:\"cost\" o:\"less to cast\"{base}",                # cost reducers
                f"o:\"create\" o:\"Treasure\"{base}",                  # treasure makers
            ],
            "reasoning": "Direct match: ramp (all subcategories)",
        },
        "mana_dorks": {
            "triggers": ["mana dork", "mana dorks", "dorks"],
            "queries": [
                f"t:creature o:\"{{T}}: Add\"{base} cmc<=2",
                f"t:creature o:\"{{T}}: Add\"{base} cmc=3",
            ],
            "reasoning": "Direct match: mana dorks specifically",
        },
        "mana_rocks": {
            "triggers": ["mana rock", "mana rocks", "rocks", "artifacts that produce mana"],
            "queries": [
                f"t:artifact o:\"{{T}}: Add\"{base} cmc<=2",
                f"t:artifact o:\"{{T}}: Add\"{base} cmc=3",
            ],
            "reasoning": "Direct match: mana rocks specifically",
        },
        "land_ramp": {
            "triggers": ["land ramp", "land search", "fetch lands", "ramp spells"],
            "queries": [
                f"o:\"search your library\" o:land t:sorcery{base}",
                f"o:\"put\" o:land o:\"onto the battlefield\"{base}",
            ],
            "reasoning": "Direct match: land-based ramp",
        },
        "cost_reducers": {
            "triggers": ["cost reducer", "cost reducers", "medallion", "medallions", "make spells cheaper"],
            "queries": [
                f"o:\"cost\" o:\"less to cast\"{base}",
                f"o:\"spells you cast cost\"{base}",
            ],
            "reasoning": "Direct match: cost reduction effects",
        },
        "removal": {
            "triggers": [
                "removal", "remove", "kill spell", "kill spells",
                "removal spells", "interaction",
            ],
            "queries": [
                f"o:\"destroy target\" (t:instant or t:sorcery){base}",
                f"o:\"exile target\" (t:instant or t:sorcery){base}",
                f"o:\"destroy all\" (t:instant or t:sorcery){base}",   # board wipes
                f"o:\"deals\" o:\"damage to\" t:instant{base}",        # damage removal
            ],
            "reasoning": "Direct match: removal (all subcategories)",
        },
        "spot_removal": {
            "triggers": ["spot removal", "targeted removal", "single target removal"],
            "queries": [
                f"o:\"destroy target\" (t:instant or t:sorcery){base}",
                f"o:\"exile target\" (t:instant or t:sorcery){base}",
            ],
            "reasoning": "Direct match: spot removal",
        },
        "board_wipes": {
            "triggers": ["board wipe", "board wipes", "sweeper", "sweepers", "wrath", "wraths"],
            "queries": [
                f"o:\"destroy all creatures\"{base}",
                f"o:\"all creatures get\" o:\"-\" (t:instant or t:sorcery){base}",
                f"o:\"exile all\" (t:instant or t:sorcery){base}",
            ],
            "reasoning": "Direct match: board wipes",
        },
        "card_draw": {
            "triggers": [
                "card draw", "draw", "draw cards", "draw engine",
                "card advantage", "draw spells",
            ],
            "queries": [
                f"o:\"draw\" t:enchantment{base}",
                f"o:\"draw\" (t:instant or t:sorcery){base}",
                f"o:\"draw\" t:creature{base}",
            ],
            "reasoning": "Direct match: card draw (all types)",
        },
        "creatures": {
            "triggers": ["creatures", "creature", "suggest creatures"],
            "queries": [
                f"t:creature{base}",
            ],
            "reasoning": "Direct match: creatures",
        },
        "lands": {
            "triggers": ["lands", "land", "land base", "mana base", "mana fixing"],
            "queries": [
                f"t:land{base}",
            ],
            "reasoning": "Direct match: lands",
        },
        "protection": {
            "triggers": [
                "protection", "protect", "hexproof", "indestructible",
                "counterspell", "counterspells", "counter",
            ],
            "queries": [
                f"o:\"hexproof\" (t:instant or t:artifact or t:equipment){base}",
                f"o:\"indestructible\" (t:instant or t:artifact){base}",
                f"o:\"counter target\" t:instant{base}",
            ],
            "reasoning": "Direct match: protection effects",
        },
        "tutors": {
            "triggers": ["tutor", "tutors", "search library"],
            "queries": [
                f"o:\"search your library\" (t:instant or t:sorcery){base}",
                f"o:\"search your library\" t:creature{base}",
            ],
            "reasoning": "Direct match: tutor effects",
        },
        "tokens": {
            "triggers": ["tokens", "token", "token generators", "token maker"],
            "queries": [
                f"o:\"create\" o:\"token\" t:creature{base}",
                f"o:\"create\" o:\"token\" t:enchantment{base}",
                f"o:\"create\" o:\"token\" (t:instant or t:sorcery){base}",
            ],
            "reasoning": "Direct match: token generation",
        },
        "recursion": {
            "triggers": [
                "recursion", "graveyard", "reanimation", "reanimate",
                "return from graveyard", "graveyard recursion",
            ],
            "queries": [
                f"o:\"return\" o:\"from your graveyard\" (t:instant or t:sorcery){base}",
                f"o:\"return\" o:\"graveyard to the battlefield\"{base}",
            ],
            "reasoning": "Direct match: graveyard recursion",
        },
        "sacrifice": {
            "triggers": ["sacrifice", "sac outlet", "sac outlets", "aristocrats"],
            "queries": [
                f"o:\"sacrifice\" o:\"whenever\"{base}",
                f"o:\"whenever\" o:\"dies\"{base}",
            ],
            "reasoning": "Direct match: sacrifice/aristocrats",
        },
        "equipment": {
            "triggers": ["equipment", "equipments", "voltron"],
            "queries": [
                f"t:equipment{base}",
            ],
            "reasoning": "Direct match: equipment",
        },
        "enchantments": {
            "triggers": ["enchantments", "enchantment", "aura", "auras"],
            "queries": [
                f"t:enchantment{base}",
            ],
            "reasoning": "Direct match: enchantments",
        },
    }
    
    # ── Determine how many results the user wants ────────────
    requested_count = None
    
    # Check for explicit numbers: "suggest 15 ramp cards", "give me 3 creatures"
    count_match = re.search(r'\b(\d+)\s+\w+\s*(card|creature|spell|suggestion)', prompt_lower)
    if count_match:
        requested_count = min(int(count_match.group(1)), 20)
    
    # Check for "all" signals: "show me all", "return all", "list all"
    if any(phrase in prompt_lower for phrase in ["all ", "every ", "as many as"]):
        requested_count = 20
    
    # Default: 5 for broad categories, let AI planner handle open-ended
    default_count = requested_count or 5

    # ── Complexity check ─────────────────────────────────────
    # Strip constraints and grammar from prompt to find core intent
    stripped = prompt_lower
    # Remove constraint patterns (prices, numbers, comparisons)
    stripped = re.sub(r'\$\d+(?:\.\d+)?', '', stripped)           # $5, $10.50
    stripped = re.sub(r'\d+\s*(?:mana|cmc|dollars?)', '', stripped)  # 3 mana, 5 cmc
    stripped = re.sub(r'(?:cmc|mana)\s*(?:<=?|>=?|=)\s*\d+', '', stripped)  # cmc<=3
    stripped = re.sub(r'\b\d+\s+or\s+(?:less|more|fewer)\b', '', stripped)  # 3 or less
    stripped = re.sub(r'\b(?:under|below|above|over|less than|more than|at most|at least|no more than|cheaper than|nothing over)\b', '', stripped)
    stripped = re.sub(r'\b(?:for|under|below)\s+\$?\d+', '', stripped)  # for $5, under 3
    stripped = re.sub(r'\$\S+', '', stripped)  # any remaining $tokens
    stripped = re.sub(r'\b\d+\b', '', stripped)  # any remaining standalone numbers
    # Remove common grammar glue
    stripped = re.sub(r'\b(?:suggest|find|recommend|show|give|list|get|need|want|looking|search|me|some|good|best|cards?|spells?|for|this|deck|please|can|you|i|a|the|my|in|of|to|and|or|with|new|add|that|are|is|it|be|do|have|has|would|could|should|will|also|too|very|pieces|options|suggestions)\b', '', stripped)
    # Clean up whitespace
    remaining = [w for w in stripped.split() if len(w) > 1]
    
    # Priority ordering: specific subcategories first
    priority_order = [
        "mana_dorks", "mana_rocks", "land_ramp", "cost_reducers",   # ramp subs
        "spot_removal", "board_wipes",                                # removal subs
        "ramp", "removal", "card_draw",                               # broad categories
        "creatures", "lands", "protection", "tutors", "tokens",
        "recursion", "sacrifice", "equipment", "enchantments",
    ]
    
    # Check if remaining words match any trigger
    matched_pattern = None
    matched_trigger = None
    for pattern_key in priority_order:
        pattern = PATTERNS[pattern_key]
        for trigger in pattern["triggers"]:
            if re.search(rf'\b{re.escape(trigger)}\b', prompt_lower):
                matched_pattern = pattern_key
                matched_trigger = trigger
                break
        if matched_pattern:
            break
    
    # If we matched a trigger, check if everything else is just constraints
    if matched_pattern:
        # Remove the trigger words from remaining
        trigger_words = matched_trigger.split()
        remaining_after_trigger = [w for w in remaining if w not in trigger_words]
        is_simple = len(remaining_after_trigger) == 0
        print(f"[AI] Bypass check: trigger='{matched_trigger}', remaining={remaining_after_trigger}, is_simple={is_simple}")
    else:
        is_simple = False
        print(f"[AI] Bypass check: no trigger matched, remaining={remaining}")
    
    
    
    # Only bypass for simple requests (1-2 meaningful words)
    # "suggest ramp cards" → ["ramp"] → bypass
    # "suggest ramp that synergizes with dragons" → ["ramp", "synergizes", "dragons"] → AI planner
    if is_simple and matched_pattern:
        pattern = PATTERNS[matched_pattern]
        return {
            "scryfall_queries": pattern["queries"],
            "reasoning": pattern["reasoning"],
            "mode": "search",
            "direct_bypass": True,
            "max_results": default_count,
        }
    
    # ── CMC-specific creature requests ───────────────────────
    # "suggest 2-drops" or "need more 3 drops" or "1-drop creatures"
    cmc_match = re.search(r'(\d+)[- ]?drops?', prompt_lower)
    if cmc_match:
        cmc = cmc_match.group(1)
        queries = [f"t:creature cmc={cmc}{base}"]
        return {
            "scryfall_queries": queries,
            "reasoning": f"Direct match: {cmc}-drop creatures",
            "mode": "search",
            "direct_bypass": True,
            "max_results": default_count,
        }
    
    # ── Creature type requests (only if simple) ──────────────
    # "suggest dragons" "need more elves" "zombie tribal"
    common_types = [
        "dragon", "elf", "elves", "goblin", "zombie", "angel", "demon",
        "merfolk", "vampire", "wizard", "warrior", "knight", "elemental",
        "beast", "dinosaur", "pirate", "spirit", "human", "cat", "dog",
        "bird", "snake", "spider", "rat", "sliver", "artifact creature",
    ]
    if is_simple:
        for creature_type in common_types:
            if re.search(rf'\b{re.escape(creature_type)}s?\b', prompt_lower):
                type_singular = creature_type.rstrip('s')
                if creature_type == "elves":
                    type_singular = "elf"
                queries = [f"t:{type_singular}{base}"]
                return {
                    "scryfall_queries": queries,
                    "reasoning": f"Direct match: {type_singular} creatures",
                    "mode": "search",
                    "direct_bypass": True,
                    "max_results": default_count,
                }
    
    # No match — fall through to AI planner
    return None


def _get_ai_plan(prompt: str, deck_context: str = None, deck_info: dict = None) -> dict:
    """Ask AI to create a Scryfall search plan."""
    
    # Build knowledge context from deck info
    knowledge = ""
    if deck_info:
        profile = deck_info.get("strategy_profile") or {}
        knowledge = build_knowledge_context(
            format_name=deck_info.get("format", "commander"),
            archetype=profile.get("primary_strategy"),
            creature_type=profile.get("primary_creature_type"),
        )
    
    system = f"""You are an expert Magic: The Gathering Scryfall query builder.
Interpret the user's request and create targeted Scryfall search queries.

Respond with ONLY valid JSON:
{{
    "mode": "search",
    "reasoning": "brief explanation of your search strategy",
    "scryfall_queries": ["query1", "query2", "query3"],
    "oracle_filters": [],
    "filter_mode": "any",
    "max_results": 10
}}

oracle_filters: oracle text terms that results SHOULD contain to match the user's intent.
Cards whose oracle text doesn't match will be deprioritized. Examples:
- "Equipment that grants trample" → oracle_filters: ["gains trample", "has trample", "gets trample", "and trample", "equipped creature"]
- "Cards that benefit from lifegain" → oracle_filters: ["whenever you gain life", "life you gained", "you gain life"]
- "Cards that make creatures bigger" → oracle_filters: ["+1/+1", "gets +", "counter on"]
- "Sacrifice outlets" → oracle_filters: ["sacrifice a creature", "sacrifice another"]
- "Suggest ramp" (general category) → oracle_filters: [] (empty — no filtering needed)
Only include oracle_filters when the user wants a SPECIFIC mechanical effect. Leave empty for broad requests.
filter_mode: "any" means matching ANY term is sufficient. "all" means ALL terms must appear.

{SCRYFALL_SYNTAX_GUIDE}

{GLOSSARY}

{REPLACEMENT_GUIDE}

{knowledge}

CRITICAL RULES:
- Generate 4-6 queries covering different angles
- At least one query should be broad enough to GUARANTEE results
- For Commander, ALWAYS use id<= for color identity and f:commander
- NEVER generate queries so narrow they return 0 results
- The last query should always be a simple broad fallback
- PRIORITIZATION: If the user's request mentions a specific creature type, theme, or synergy, the MAJORITY of queries (3-4 out of 6) should target that specific angle. Only 1-2 queries should be generic fallbacks.
- Example: "ramp for dragons" should generate 4 dragon-specific ramp queries (otag:tribal-dragon, o:dragon o:cost o:less, t:dragon o:add, o:dragon o:mana) and only 1-2 generic ramp queries as fallback.
- Example: "removal" with no qualifier should generate broad removal queries across all subcategories.
- The user's specificity determines the query mix — specific request = specific queries.
"""

    user_msg = f"User request: {prompt}"
    if deck_context:
        user_msg += f"\n\nDeck context:\n{deck_context}"
    
    # Include playbook scryfall hints if available
    if deck_info:
        playbook = (deck_info.get("strategy_profile") or {}).get("archetype_playbook", {})
        category_guidance = playbook.get("category_guidance", {})
        if category_guidance:
            hint_lines = ["Deck-specific Scryfall query hints:"]
            for cat, guidance in category_guidance.items():
                hints = guidance.get("scryfall_hints", [])
                if hints:
                    hint_lines.append(f"  {cat}: {', '.join(hints)}")
            # Also include unique categories
            for cat, guidance in playbook.get("unique_categories", {}).items():
                hints = guidance.get("scryfall_hints", [])
                if hints:
                    hint_lines.append(f"  {cat}: {', '.join(hints)}")
            if len(hint_lines) > 1:
                user_msg += "\n\n" + "\n".join(hint_lines)

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