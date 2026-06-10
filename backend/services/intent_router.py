"""
Intent classifier for AI suggestion requests.
Routes user prompts to specialized prompt builders based on detected intent.
Uses keyword matching as the fast path with AI fallback for ambiguous prompts.
"""

import os
import json
from openai import OpenAI


# Intent types
INTENT_SUGGEST = "suggest"    # User wants card recommendations
INTENT_CUTS = "cuts"          # User wants to know what to remove
INTENT_ANALYZE = "analyze"    # User wants deck health diagnosis
INTENT_SWAP = "swap"          # User wants to replace cards (cut + add)
INTENT_DISCUSS = "discuss"    # User wants to talk through deck ideas (no specific suggestions)


def classify_intent(prompt: str, has_deck: bool = False) -> dict:
    """
    Classify user intent from natural language prompt.
    Uses AI classification for reliability — keyword matching was too fragile.
    """
    prompt_lower = prompt.lower().strip()

    # Only use keywords for the most unambiguous single-word triggers
    if prompt_lower in ["analyze", "analysis", "review", "evaluate"]:
        return {"intent": INTENT_ANALYZE, "confidence": "high", "method": "keyword"}
    
    # Everything else goes to AI for reliable classification
    if has_deck:
        intent = _ai_classify(prompt)
        return {"intent": intent, "confidence": "high", "method": "ai"}

    return {"intent": INTENT_SUGGEST, "confidence": "medium", "method": "default"}


def _ai_classify(prompt: str) -> str:
    """
    Use AI to classify ambiguous prompts.
    Lightweight call — ~100 tokens in, ~10 tokens out.
    Uses a fresh client to avoid stale connection issues.
    """
    system = """Classify this Magic: The Gathering deck question into exactly one category.
Respond with ONLY one word — no explanation:

suggest — user wants card recommendations or is describing cards they want (e.g., "cards that benefit from lifegain", "trample cards", "equipment that grants flying", "cards that synergize with sacrifice")
cuts — user wants to know which cards to REMOVE
analyze — user wants to understand their deck's strengths and weaknesses
swap — user wants to REPLACE specific cards with better options
discuss — user is asking a THEORY question about how MTG works, not requesting specific cards (e.g., "how does trample work", "is lifegain viable in commander", "what makes a good mana base")

IMPORTANT: If the prompt mentions "cards", "cards that", "suggest", or describes card effects, it is ALWAYS suggest, never discuss."""

    try:
        fresh_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = fresh_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
            max_tokens=10,
        )
        result = response.choices[0].message.content.strip().lower()

        if result in (INTENT_SUGGEST, INTENT_CUTS, INTENT_ANALYZE, INTENT_SWAP, INTENT_DISCUSS):
            return result

        return INTENT_SUGGEST

    except Exception:
        return INTENT_SUGGEST