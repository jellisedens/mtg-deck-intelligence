"""
Search Specification Generator

Takes a clarified/refined prompt and generates a structured search specification.
This spec drives both Scryfall queries AND post-search filtering.

Replaces the AI planner for clarified prompts — one focused call instead of
a general-purpose planner that forgets oracle filters.

The spec is structured data that code can enforce deterministically.
"""

import os
import json
import time
from openai import OpenAI

_client = None

def _get_client():
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client


def generate_search_spec(prompt: str, color_identity: list = None,
                         deck_format: str = "commander") -> dict:
    """
    Generate a structured search specification from a user's prompt.
    
    Returns a spec dict with:
    - intent_summary: what the user wants (for debugging/logging)
    - oracle_required: terms that MUST appear in oracle text
    - oracle_preferred: terms that SHOULD appear (boost relevance)
    - match_rule: how to combine required + preferred
    - scryfall_queries: targeted queries to execute
    - max_results: how many cards to return
    """
    t_start = time.time()
    
    # Build color identity filter for queries
    ci_filter = ""
    if color_identity:
        wubrg_order = "WUBRG"
        sorted_colors = "".join(c for c in wubrg_order if c in color_identity)
        if sorted_colors:
            ci_filter = f" id<={sorted_colors}"
    
    format_filter = f" f:{deck_format}" if deck_format else ""
    base_filter = format_filter + ci_filter

    system = f"""You are an expert Magic: The Gathering card search specialist.

Given a user's card search request, generate a precise search specification.

Respond with ONLY valid JSON:
{{
    "intent_summary": "One sentence describing exactly what the user wants",
    "oracle_required": ["term1", "term2"],
    "oracle_preferred": ["term1", "term2", "term3"],
    "match_rule": "all_required_any_preferred",
    "scryfall_queries": ["query1", "query2", "query3", "query4"],
    "max_results": 8
}}

FIELD DEFINITIONS:

oracle_required: Terms that MUST appear in a card's oracle text for it to be relevant.
  These are the non-negotiable terms. If a card doesn't contain ALL of these, it's irrelevant.
  Keep this tight — usually 1-2 terms max.
  Examples:
    - "Cards that grant trample" → oracle_required: ["trample"]
    - "Cards that trigger on life gain" → oracle_required: ["life"]  
    - "Sacrifice outlets" → oracle_required: ["sacrifice"]
    - "Cards that return things from graveyard" → oracle_required: ["graveyard"]

oracle_preferred: Terms that indicate the card matches the specific INTENT, not just the topic.
  Cards matching these get higher priority. Used to distinguish grant-vs-have, payoff-vs-source, etc.
  Examples:
    - "Grant trample to creatures" → oracle_preferred: ["equipped creature", "enchanted creature", "target creature", "creatures you control", "gains trample", "gets trample", "has trample"]
    - "Cards that trigger on life gain" → oracle_preferred: ["whenever you gain life", "whenever a creature you control gains", "life you gained"]
    - "Sacrifice outlets" → oracle_preferred: ["sacrifice a creature", "sacrifice another", "sacrifice a permanent"]
    - "Cards that make creatures bigger" → oracle_preferred: ["+1/+1", "gets +", "counter on", "creatures you control get"]

match_rule: How to combine required and preferred. One of:
  - "all_required_any_preferred" — MUST have all required, BONUS for preferred (most common)
  - "any_required_any_preferred" — must have at least one required, bonus for preferred
  - "all_required_only" — strict, only required terms matter

scryfall_queries: 4-6 targeted Scryfall queries. Rules:
  - ALWAYS append "{base_filter}" to every query for format + color identity
  - Generate queries from MOST SPECIFIC to LEAST SPECIFIC
  - First 3-4 queries should be highly targeted to the exact intent
  - Last 1-2 queries should be broader fallbacks that guarantee results
  - For "grant X" intents, search equipment/auras/instants that mention X
  - For "has X" intents, search creatures with keyword X
  - For "triggers on X" intents, search for "whenever" + X patterns
  
  The base filter for this deck is: "{base_filter}"
  APPEND this to every query. Example: o:"trample" t:equipment{base_filter}

EXAMPLES:

User: "Equipment and auras that grant trample to a creature"
{{
    "intent_summary": "Cards that give trample to other creatures via equipment or aura",
    "oracle_required": ["trample"],
    "oracle_preferred": ["equipped creature", "enchanted creature", "target creature", "creatures you control", "gains trample", "gets trample"],
    "match_rule": "all_required_any_preferred",
    "scryfall_queries": [
        "o:trample (t:equipment or t:aura){base_filter}",
        "o:\\"gains trample\\"{base_filter}",
        "o:\\"gets trample\\" (t:instant or t:sorcery){base_filter}",
        "o:trample o:\\"creatures you control\\"{base_filter}",
        "o:trample (t:artifact or t:enchantment){base_filter}"
    ],
    "max_results": 8
}}

User: "Cards that trigger whenever I gain life"
{{
    "intent_summary": "Permanents with abilities that trigger on life gain events",
    "oracle_required": ["life"],
    "oracle_preferred": ["whenever you gain life", "whenever a creature", "life you gained", "each time you gain"],
    "match_rule": "all_required_any_preferred",
    "scryfall_queries": [
        "o:\\"whenever you gain life\\"{base_filter}",
        "o:\\"life you gained\\"{base_filter}",
        "o:\\"each time you gain life\\"{base_filter}",
        "o:\\"gain life\\" o:\\"whenever\\"{base_filter}",
        "o:\\"gain life\\" (t:creature or t:enchantment){base_filter}"
    ],
    "max_results": 8
}}

User: "All cards related to sacrifice"
{{
    "intent_summary": "All cards that interact with sacrifice mechanics",
    "oracle_required": ["sacrifice"],
    "oracle_preferred": [],
    "match_rule": "all_required_only",
    "scryfall_queries": [
        "o:\\"sacrifice a creature\\"{base_filter}",
        "o:\\"whenever you sacrifice\\"{base_filter}",
        "o:\\"whenever a creature dies\\"{base_filter}",
        "o:sacrifice (t:creature or t:artifact or t:enchantment){base_filter}",
        "o:sacrifice{base_filter}"
    ],
    "max_results": 8
}}"""

    try:
        client = _get_client()
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=500,
        )
        content = response.choices[0].message.content.strip()
        content = content.replace("```json", "").replace("```", "").strip()
        spec = json.loads(content)

        # Validate required fields
        spec.setdefault("oracle_required", [])
        spec.setdefault("oracle_preferred", [])
        spec.setdefault("match_rule", "all_required_any_preferred")
        spec.setdefault("scryfall_queries", [])
        spec.setdefault("max_results", 8)
        spec.setdefault("intent_summary", prompt)

        print(f"[AI] Search spec generated ({time.time() - t_start:.1f}s): {spec['intent_summary']}")
        print(f"[AI] Required: {spec['oracle_required']}, Preferred: {spec['oracle_preferred'][:3]}")

        return spec

    except Exception as e:
        print(f"[AI] Search spec failed: {e}")
        # Return a minimal spec so the pipeline continues
        return {
            "intent_summary": prompt,
            "oracle_required": [],
            "oracle_preferred": [],
            "match_rule": "all_required_any_preferred",
            "scryfall_queries": [],
            "max_results": 8,
            "error": str(e),
        }


def apply_spec_filter(results: list, spec: dict) -> list:
    """
    Apply the search spec's oracle filters to search results.
    
    Enforces oracle_required as hard filters.
    Uses oracle_preferred for relevance scoring and prioritization.
    """
    oracle_required = [t.lower() for t in spec.get("oracle_required", [])]
    oracle_preferred = [t.lower() for t in spec.get("oracle_preferred", [])]
    match_rule = spec.get("match_rule", "all_required_any_preferred")

    if not oracle_required and not oracle_preferred:
        return results

    scored = []
    filtered_out = 0

    for card in results:
        oracle = (card.get("oracle_text") or "").lower()

        # Check required terms
        if match_rule in ("all_required_any_preferred", "all_required_only"):
            has_all_required = all(term in oracle for term in oracle_required)
        else:  # any_required
            has_all_required = any(term in oracle for term in oracle_required) if oracle_required else True

        if oracle_required and not has_all_required:
            filtered_out += 1
            continue

        # Score by preferred terms
        preferred_score = sum(1 for term in oracle_preferred if term in oracle)
        scored.append((card, preferred_score))

    # Sort by preferred score (most relevant first), then EDHREC rank
    scored.sort(key=lambda x: (-x[1], x[0].get("edhrec_rank") or 999999))
    filtered_results = [card for card, _ in scored]

    if filtered_out > 0 or oracle_required:
        print(f"[AI] Spec filter: {len(filtered_results)} pass (required: {oracle_required}), {filtered_out} removed")

    # If spec filtering was too aggressive, fall back to original results with priority
    if len(filtered_results) < 3 and len(results) > 3:
        print(f"[AI] Spec filter too aggressive ({len(filtered_results)} results), relaxing to priority mode")
        # Keep filtered results at top, add non-matching as fallback
        seen = {c.get("scryfall_id") for c in filtered_results}
        for card in results:
            if card.get("scryfall_id") not in seen:
                filtered_results.append(card)
                if len(filtered_results) >= 20:
                    break

    return filtered_results