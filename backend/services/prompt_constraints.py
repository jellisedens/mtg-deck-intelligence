"""
Prompt Constraint System

Two layers:
1. Deterministic constraints (CMC, price) — extracted by regex, enforced by code
2. Semantic constraints (oracle filters) — extracted by AI planner, enforced by code

The AI understands what the user means. Code enforces it.
"""

import re


def extract_deterministic_constraints(prompt: str) -> dict:
    """
    Extract constraints that can be reliably parsed from the prompt.
    These are numeric/factual — no interpretation needed.
    """
    prompt_lower = prompt.lower()
    constraints = {}

    # ── CMC constraints ──────────────────────────────────
    cmc_patterns = [
        r'(\d+)\s+or\s+less\s*(?:mana|cmc)?',
        r'(?:under|below|less than|cheaper than)\s+(\d+)\s*(?:mana|cmc)?',
        r'(?:cmc|mana\s*(?:cost|value)?)\s*(?:of\s+)?(\d+)\s+or\s+(?:less|lower|under)',
        r'(?:cmc|cost)\s*<=?\s*(\d+)',
        r'(?:nothing|no cards?)\s+(?:over|above|more than)\s+(\d+)\s*(?:mana|cmc)?',
        r'(?:max|maximum)\s+(?:cmc|mana|cost)\s*(?:of\s+)?(\d+)',
        r'(?:for|at|costing)\s+(\d+)\s+(?:mana\s+)?or\s+less',
    ]
    for pattern in cmc_patterns:
        match = re.search(pattern, prompt_lower)
        if match:
            constraints["max_cmc"] = int(match.group(1))
            break

    if "max_cmc" not in constraints:
        if "cheap" in prompt_lower or "low cost" in prompt_lower:
            constraints["max_cmc"] = 3

    # ── Price constraints ────────────────────────────────
    price_patterns = [
        r'(?:under|below|less than|cheaper than)\s+\$(\d+(?:\.\d+)?)',
        r'(?:nothing|no cards?)\s+(?:over|above|more than)\s+\$(\d+(?:\.\d+)?)',
        r'\$(\d+(?:\.\d+)?)\s+or\s+(?:less|under|cheaper)',
        r'(?:max|maximum)\s+(?:price|cost)\s*(?:of\s+)?\$(\d+(?:\.\d+)?)',
        r'(?:under|below|less than)\s+(\d+(?:\.\d+)?)\s+dollars?',
        r'(?:nothing|no cards?)\s+(?:over|above)\s+(\d+(?:\.\d+)?)\s+dollars?',
        r'(?:more|no more)\s+(?:than|expensive than)\s+\$?(\d+(?:\.\d+)?)',
    ]
    for pattern in price_patterns:
        match = re.search(pattern, prompt_lower)
        if match:
            constraints["max_price"] = float(match.group(1))
            break

    if "max_price" not in constraints and "budget" in prompt_lower:
        constraints["max_price"] = 5.0

    return constraints


def apply_deterministic_constraints(results: list, constraints: dict) -> list:
    """Apply CMC and price constraints as hard filters."""
    if not constraints:
        return results

    original_count = len(results)
    filtered = results

    max_cmc = constraints.get("max_cmc")
    if max_cmc is not None:
        filtered = [c for c in filtered if (c.get("cmc") or 0) <= max_cmc]

    max_price = constraints.get("max_price")
    if max_price is not None:
        def get_price(card):
            price_str = (card.get("prices") or {}).get("usd")
            if price_str:
                try:
                    return float(price_str)
                except (ValueError, TypeError):
                    pass
            return 0
        filtered = [c for c in filtered if get_price(c) <= max_price or get_price(c) == 0]

    removed = original_count - len(filtered)
    if removed > 0:
        parts = []
        if max_cmc is not None:
            parts.append(f"cmc<={max_cmc}")
        if max_price is not None:
            parts.append(f"price<=${max_price}")
        print(f"[AI] Deterministic constraints [{', '.join(parts)}] removed {removed} cards, {len(filtered)} remain")

    return filtered


def apply_oracle_filters(results: list, oracle_filters: list, filter_mode: str = "any") -> list:
    """
    Apply AI-generated oracle text filters to search results.
    
    oracle_filters: list of terms the AI says must appear in oracle text
    filter_mode: "any" = card matches if ANY filter term appears
                 "all" = card must match ALL filter terms
    
    Falls back gracefully — if filtering leaves < 3 cards, returns
    all cards with matching ones prioritized.
    """
    if not oracle_filters:
        return results

    matching = []
    non_matching = []

    for card in results:
        oracle = (card.get("oracle_text") or "").lower()
        
        if filter_mode == "all":
            matches = all(term.lower() in oracle for term in oracle_filters)
        else:
            matches = any(term.lower() in oracle for term in oracle_filters)
        
        if matches:
            matching.append(card)
        else:
            non_matching.append(card)

    print(f"[AI] Oracle filters {oracle_filters} ({filter_mode}): {len(matching)} match, {len(non_matching)} don't")

    # If enough matches, cap the non-matching fallbacks
    if len(matching) >= 5:
        max_fallback = max(2, len(matching) // 4)
        return matching + non_matching[:max_fallback]
    elif len(matching) >= 3:
        return matching + non_matching[:5]
    else:
        # Not enough matches — prioritize but keep everything
        # The AI planner's filters may have been too narrow
        print(f"[AI] Oracle filter too aggressive ({len(matching)} matches), keeping all with priority")
        return matching + non_matching