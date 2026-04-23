"""
Intent classifier for AI suggestion requests.
Routes user prompts to specialized prompt builders based on detected intent.
Uses keyword matching as the fast path with AI fallback for ambiguous prompts.
"""

import os
import json
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL = "gpt-4o-mini"

# Intent types
INTENT_SUGGEST = "suggest"    # User wants card recommendations
INTENT_CUTS = "cuts"          # User wants to know what to remove
INTENT_ANALYZE = "analyze"    # User wants deck health diagnosis
INTENT_SWAP = "swap"          # User wants to replace cards (cut + add)


def classify_intent(prompt: str, has_deck: bool = False) -> dict:
    """
    Classify user intent from natural language prompt.
    
    Returns:
        {
            "intent": "suggest" | "cuts" | "analyze" | "swap",
            "confidence": "high" | "medium",
            "method": "keyword" | "ai_fallback"
        }
    """
    prompt_lower = prompt.lower().strip()

    # === KEYWORD MATCHING (fast path) ===

    # Swap signals — user wants to both cut AND add
    swap_signals = [
        "make room for", "replace", "swap", "upgrade",
        "trade out", "switch out", "instead of",
        "better version", "better option",
    ]

    # Cut signals — user wants to remove cards
    cut_signals = [
        "cut", "remove", "drop", "take out", "weakest",
        "worst card", "what to remove", "trim",
        "too many", "over-represented", "redundant",
    ]

    # Analyze signals — user wants deck evaluation
    analyze_signals = [
        "analyze", "what's wrong", "whats wrong", "evaluate",
        "diagnose", "review", "how's my deck", "hows my deck",
        "how does my deck", "deck health", "performance",
        "is my deck", "rate my", "grade my",
        "feels slow", "feels weak", "feels inconsistent",
        "struggling", "not performing", "problems with",
    ]

    # Add signals — user wants card suggestions
    add_signals = [
        "suggest", "recommend", "find", "need",
        "best cards", "good cards", "looking for",
        "what cards", "show me", "list",
    ]

    has_swap = any(s in prompt_lower for s in swap_signals)
    has_cut = any(s in prompt_lower for s in cut_signals)
    has_analyze = any(s in prompt_lower for s in analyze_signals)
    has_add = any(s in prompt_lower for s in add_signals)

    # Combined signals
    if has_swap:
        return {"intent": INTENT_SWAP, "confidence": "high", "method": "keyword"}

    if has_cut and has_add:
        return {"intent": INTENT_SWAP, "confidence": "high", "method": "keyword"}

    if has_cut:
        return {"intent": INTENT_CUTS, "confidence": "high", "method": "keyword"}

    if has_analyze:
        return {"intent": INTENT_ANALYZE, "confidence": "high", "method": "keyword"}

    if has_add:
        return {"intent": INTENT_SUGGEST, "confidence": "high", "method": "keyword"}

    # === NO STRONG MATCH — AI FALLBACK ===
    if has_deck:
        intent = _ai_classify(prompt)
        return {"intent": intent, "confidence": "medium", "method": "ai_fallback"}

    # No deck context and no keywords — default to suggest
    return {"intent": INTENT_SUGGEST, "confidence": "medium", "method": "keyword"}


def _ai_classify(prompt: str) -> str:
    """
    Use AI to classify ambiguous prompts.
    Lightweight call — ~100 tokens in, ~10 tokens out.
    """
    system = """Classify this Magic: The Gathering deck question into exactly one category.
Respond with ONLY one word — no explanation:

suggest — user wants card recommendations to ADD to their deck
cuts — user wants to know which cards to REMOVE
analyze — user wants to understand their deck's strengths and weaknesses
swap — user wants to REPLACE specific cards with better options"""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
            max_tokens=10,
        )
        result = response.choices[0].message.content.strip().lower()

        if result in (INTENT_SUGGEST, INTENT_CUTS, INTENT_ANALYZE, INTENT_SWAP):
            return result

        return INTENT_SUGGEST  # safe default

    except Exception:
        return INTENT_SUGGEST  # safe default on error