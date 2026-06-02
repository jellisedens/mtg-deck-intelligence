"""
Effect Clarifier — AI-Powered Intent Detection

Uses a lightweight AI call to determine if a user's prompt is ambiguous
and needs clarification before searching. Generates intent-based options
dynamically — no hardcoded aliases or keyword lists.

Only fires when:
- Prompt didn't match category clarifier (ramp, removal, etc.)
- Prompt didn't match direct bypass patterns
- Prompt is short enough to be potentially ambiguous (< 8 words)

Adds ~1-2s latency only for ambiguous prompts.
"""

import os
import re
import json
from openai import OpenAI


_client = None

def _get_client():
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client


CLARIFY_SYSTEM = """You are an expert Magic: The Gathering advisor.

Determine if this user prompt needs intent clarification before searching for cards.

Rules:
- If the user's intent is CLEAR and SPECIFIC, respond: {"needs_clarification": false}
- If the user's intent is AMBIGUOUS (could mean multiple different things), respond with clarification options
- General categories like "suggest ramp" or "need removal" are CLEAR — do NOT clarify these
- Prompts about granting/giving abilities, synergizing with mechanics, or interacting with effects are often AMBIGUOUS
- Only suggest clarification when the different intents would lead to meaningfully DIFFERENT card searches

When clarification is needed, respond with:
{
    "needs_clarification": true,
    "question": "Short question about intent (e.g., 'What's the goal with lifegain?')",
    "options": [
        {"label": "Short label (3-5 words)", "description": "One sentence explaining this intent with 2-3 example card names"},
        {"label": "Short label", "description": "One sentence with examples"},
        {"label": "Short label", "description": "One sentence with examples"},
        {"label": "All related cards", "description": "Everything related to this mechanic or effect"}
    ]
}

Provide 3-4 options maximum. Each option should represent a DIFFERENT INTENT, not a different card type.
Bad options (card-type based): "Equipment with trample" vs "Instants with trample"
Good options (intent-based): "Cards that GRANT trample to creatures" vs "Creatures that HAVE trample" vs "Cards that BENEFIT from trample damage"

The last option should always be an "all/everything" catch-all.

Examples of prompts that NEED clarification:
- "trample cards" → Grant vs Have vs Benefit from
- "cards that care about life" → Lifegain payoffs vs Lifegain sources vs Life as resource
- "sacrifice stuff" → Sac outlets vs Death triggers vs Fodder vs Recursion
- "graveyard cards" → Reanimate vs Self-mill vs Graveyard hate vs Cast from graveyard
- "make my creatures bigger" → +1/+1 counters vs Anthem effects vs Pump spells vs Equipment

Examples of prompts that DO NOT need clarification:
- "suggest ramp" → clear category
- "cards that grant trample to a creature" → clear intent (grant)
- "Equipment and auras that give flying" → clear intent and card type
- "suggest some good cards" → clear (general suggestions)
- "what should I cut" → clear (cuts intent)
- "Creatures that trigger whenever I gain life" → clear and specific

Respond with ONLY valid JSON, no markdown."""


def check_for_effect_clarification(prompt: str) -> dict | None:
    """
    Use a lightweight AI call to determine if a prompt needs intent clarification.
    Returns a clarification dict if yes, None if the prompt is clear enough.
    
    Only fires for short, potentially ambiguous prompts.
    """
    prompt_lower = prompt.lower().strip()

    # ── Skip conditions (don't waste an AI call) ─────────────

    # Already specific — 8+ words means the user has given enough context
    if len(prompt_lower.split()) >= 8:
        return None

    # Very short generic prompts are handled by category clarifier
    if len(prompt_lower.split()) <= 2:
        return None

    # This is a rewritten clarification response from the frontend
    if re.search(r'^suggest\s+.+\s+for\s+\w+$', prompt_lower):
        return None

    # This IS a clarification response — user already refined
    # These are descriptive phrases that came from clicking an option
    if any(prompt_lower.startswith(p) for p in [
        "cards that grant", "cards that trigger", "cards that benefit",
        "cards that give", "cards that create", "cards that return",
        "cards that put", "cards that exile", "cards that destroy",
        "equipment and aura", "equipment that", "creatures that",
        "instant", "sorcery", "enchantment", "all cards",
        "all related", "everything related", "everything that",
        "grant ", "place ", "free ", "reanimate", "reanimation",
        "evasion", "damage trigger", "damage multiplier",
        "token generator", "blink enabler",
    ]):
        return None

    # Non-suggest intents — cuts, analyze, swap don't need effect clarification
    non_suggest_indicators = [
        "cut", "remove", "drop", "take out",
        "analyze", "analysis", "review", "evaluate", "how good",
        "swap", "replace", "switch",
    ]
    if any(word in prompt_lower for word in non_suggest_indicators):
        return None

    # ── AI clarification check ───────────────────────────────
    try:
        client = _get_client()
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": CLARIFY_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
            max_tokens=300,
        )
        content = response.choices[0].message.content.strip()
        content = content.replace("```json", "").replace("```", "").strip()
        result = json.loads(content)

        if not result.get("needs_clarification"):
            return None

        # Validate the response has proper structure
        options = result.get("options", [])
        if not options or len(options) < 2:
            return None

        # Ensure options have label and description
        valid_options = []
        for opt in options:
            if isinstance(opt, dict) and opt.get("label") and opt.get("description"):
                valid_options.append({
                    "label": opt["label"],
                    "description": opt["description"],
                })

        if len(valid_options) < 2:
            return None

        print(f"[AI] Effect clarifier triggered: {result.get('question', '?')} ({len(valid_options)} options)")

        return {
            "needs_clarification": True,
            "clarification_question": result.get("question", "What are you looking for?"),
            "clarification_options": valid_options,
            "summary": None,
            "suggestions": [],
            "cuts": [],
            "strategy_notes": None,
            "_clarification_type": "ai_effect",
        }

    except Exception as e:
        # If the AI call fails, proceed without clarification
        print(f"[AI] Effect clarifier failed (non-fatal): {e}")
        return None