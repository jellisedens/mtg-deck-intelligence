"""
Prompt Constraint System

Two layers:
1. Deterministic constraints (CMC, price) — extracted by regex, enforced by code
2. Oracle relevance scoring — extract terms from user's prompt, prioritize results that match
3. AI oracle filters — from planner when available, applied as additional filter

The key insight: if the user says "trample", cards with "trample" in oracle text
are more relevant than cards without it. No hardcoding needed — the user's own
words become the relevance signal.
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

    # Handle trailing dollar: "5$", "5 $", "10$"
    if "max_price" not in constraints:
        trailing_dollar = re.search(r'(\d+(?:\.\d+)?)\s*\$', prompt_lower)
        if trailing_dollar:
            constraints["max_price"] = float(trailing_dollar.group(1))

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


def extract_prompt_oracle_terms(prompt: str) -> list[str]:
    """
    Extract terms from the user's prompt that are likely to appear in card oracle text.
    These become relevance signals — cards containing these terms are prioritized.
    
    This is universal: no predefined keyword list. Instead, we filter out
    common English filler and MTG meta-language, leaving the mechanical terms.
    """
    prompt_lower = prompt.lower().strip()
    
    # Words that are meta-language (about the game/request) not card text
    meta_words = {
        # Request language
        "suggest", "find", "recommend", "show", "give", "list", "get",
        "need", "want", "looking", "search", "cards", "card", "spells",
        "spell", "some", "good", "best", "great", "strong", "powerful",
        "any", "all", "types", "type", "options", "suggestions", "pieces",
        # Pronouns/articles/prepositions
        "i", "me", "my", "the", "a", "an", "for", "to", "of", "in",
        "and", "or", "with", "that", "which", "this", "these", "those",
        "can", "could", "would", "should", "will", "do", "does",
        "are", "is", "it", "be", "have", "has", "not", "no",
        # MTG meta-language (about the game, not on cards)
        "deck", "commander", "creature", "creatures", "permanent", "permanents",
        "mana", "cmc", "budget", "cheap", "expensive",
        "equipment", "aura", "auras", "instant", "sorcery", "enchantment",
        "artifact", "artifacts", "land", "lands",
        # Intent words
        "grant", "grants", "give", "gives", "make", "makes",
        "provide", "provides", "benefit", "benefits", "interact",
        "synergize", "synergy", "care", "cares", "about",
        "use", "using", "trigger", "triggers",
        # Common qualifiers
        "under", "over", "less", "more", "than", "below", "above",
        "also", "too", "very", "really", "just", "only",
    }
    
    # Split and filter
    words = prompt_lower.split()
    meaningful = []
    for word in words:
        # Remove punctuation
        clean = re.sub(r'[^\w+/-]', '', word)
        if not clean or len(clean) < 3:
            continue
        if clean in meta_words:
            continue
        # Skip numbers (handled by CMC/price constraints)
        if clean.isdigit():
            continue
        meaningful.append(clean)
    
    # Also extract multi-word phrases that commonly appear in oracle text
    oracle_phrases = []
    phrase_patterns = [
        r"(can't be blocked)",
        r"(deals? combat damage)",
        r"(enter(?:s|ing)? the battlefield)",
        r"(leaves? the battlefield)",
        r"(\+1/\+1 counter)",
        r"(-1/-1 counter)",
        r"(gain(?:s)? life)",
        r"(lose(?:s)? life)",
        r"(draw(?:s)? a card)",
        r"(search your library)",
        r"(destroy(?:s)? target)",
        r"(exile(?:s)? target)",
        r"(sacrifice a creature)",
        r"(double strike)",
        r"(first strike)",
    ]
    for pattern in phrase_patterns:
        if re.search(pattern, prompt_lower):
            match = re.search(pattern, prompt_lower)
            if match:
                oracle_phrases.append(match.group(1))
    
    return meaningful + oracle_phrases


def apply_oracle_relevance(results: list, prompt: str, ai_oracle_filters: list = None) -> list:
    """
    Prioritize search results by relevance to the user's prompt.
    
    Uses two sources:
    1. AI-generated oracle_filters (when the planner provides them)
    2. Terms extracted directly from the user's prompt
    
    Cards matching either source are prioritized. Cards matching neither
    are pushed to the back. If enough matches exist, non-matching cards
    are capped to prevent dilution.
    """
    # Combine AI filters with prompt-extracted terms
    prompt_terms = extract_prompt_oracle_terms(prompt)
    ai_terms = ai_oracle_filters or []
    
    # AI terms take priority (more precise), prompt terms as fallback
    all_terms = list(set(ai_terms + prompt_terms))
    
    if not all_terms:
        return results
    
    # Score each result by how many terms match its oracle text
    scored = []
    for card in results:
        oracle = (card.get("oracle_text") or "").lower()
        match_count = sum(1 for term in all_terms if term in oracle)
        scored.append((card, match_count))
    
    # Split into matching and non-matching
    matching = [(card, score) for card, score in scored if score > 0]
    non_matching = [card for card, score in scored if score == 0]
    
    # Sort matching cards by match count (most relevant first), then by EDHREC rank
    matching.sort(key=lambda x: (-x[1], x[0].get("edhrec_rank") or 999999))
    matched_cards = [card for card, _ in matching]
    
    if matched_cards:
        terms_used = [t for t in all_terms if any(t in (c.get("oracle_text") or "").lower() for c in matched_cards)]
        print(f"[AI] Oracle relevance: {len(matched_cards)} match terms {terms_used[:5]}, {len(non_matching)} don't")
        
        # Cap non-matching based on how many matches we have
        if len(matched_cards) >= 8:
            return matched_cards
        elif len(matched_cards) >= 5:
            return matched_cards + non_matching[:max(1, len(matched_cards) // 5)]
        elif len(matched_cards) >= 3:
            return matched_cards + non_matching[:3]
        else:
            # Few matches — keep all but prioritize
            return matched_cards + non_matching
    
    return results


def apply_oracle_filters(results: list, oracle_filters: list, filter_mode: str = "any") -> list:
    """
    Apply AI-generated oracle text filters to search results.
    DEPRECATED — use apply_oracle_relevance instead, which combines
    AI filters with prompt-extracted terms for more reliable results.
    Kept for backward compatibility.
    """
    return apply_oracle_relevance(results, "", ai_oracle_filters=oracle_filters)