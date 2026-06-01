"""
Effect Clarifier

Detects when a user's prompt is about a specific mechanical effect
and offers clarification options so the system returns exactly what they want.

This runs BEFORE any AI calls or Scryfall searches — it's pure pattern matching.
When clarification is returned, the user's selection becomes the refined prompt,
which then flows through the normal AI planner → search → filter pipeline.
"""

import re

# MTG keyword abilities that commonly need grant-vs-has clarification
KEYWORD_ABILITIES = [
    "trample", "flying", "hexproof", "indestructible", "haste",
    "deathtouch", "lifelink", "vigilance", "menace", "double strike",
    "first strike", "reach", "flash", "ward", "shroud",
    "unblockable", "infect", "wither",
]

# Mechanics that have "synergize with" patterns
SYNERGY_MECHANICS = {
    "lifegain": {
        "aliases": ["life gain", "lifegain", "gaining life", "gain life", "lifelink"],
        "question": "What kind of lifegain cards are you looking for?",
        "options": [
            {"label": "Lifegain triggers", "description": "Cards that trigger whenever I gain life (Ajani's Pridemate, Soul Warden)"},
            {"label": "Direct lifegain", "description": "Cards that gain me life directly (lifelink, life gain spells)"},
            {"label": "Life as resource", "description": "Cards that pay life as a cost and benefit from having high life"},
            {"label": "All lifegain", "description": "All cards that interact with life gain"},
        ],
    },
    "sacrifice": {
        "aliases": ["sacrifice", "sacrificing", "sac outlet", "sac"],
        "question": "What kind of sacrifice support are you looking for?",
        "options": [
            {"label": "Free sac outlets", "description": "Free sacrifice outlets (Viscera Seer, Ashnod's Altar)"},
            {"label": "Death triggers", "description": "Cards that trigger when creatures die (Blood Artist, Zulaport Cutthroat)"},
            {"label": "Token fodder", "description": "Token generators to use as sacrifice fodder"},
            {"label": "Graveyard recursion", "description": "Cards that return creatures from graveyard after sacrifice"},
            {"label": "All sacrifice", "description": "All sacrifice-related cards"},
        ],
    },
    "counters": {
        "aliases": ["+1/+1 counter", "counters", "+1 counter", "counter synergy"],
        "question": "What kind of counter support are you looking for?",
        "options": [
            {"label": "Place counters", "description": "Cards that put +1/+1 counters on creatures"},
            {"label": "Counter triggers", "description": "Cards that trigger when counters are placed (Hardened Scales)"},
            {"label": "Proliferate", "description": "Cards that proliferate or multiply counters"},
            {"label": "Move counters", "description": "Cards that move or distribute counters"},
            {"label": "All counters", "description": "All +1/+1 counter cards"},
        ],
    },
    "graveyard": {
        "aliases": ["graveyard", "graveyard synergy", "from the graveyard"],
        "question": "What kind of graveyard interaction are you looking for?",
        "options": [
            {"label": "Reanimation", "description": "Cards that return creatures from graveyard to battlefield"},
            {"label": "Self-mill", "description": "Cards that fill my graveyard (self-mill, discard outlets)"},
            {"label": "Graveyard hate", "description": "Cards that exile opponents' graveyards"},
            {"label": "Cast from graveyard", "description": "Cards that cast spells from the graveyard (flashback, escape)"},
            {"label": "All graveyard", "description": "All graveyard-related cards"},
        ],
    },
    "tokens": {
        "aliases": ["token", "tokens", "token generation", "create tokens"],
        "question": "What kind of token support are you looking for?",
        "options": [
            {"label": "Token generators", "description": "Cards that create creature tokens repeatedly"},
            {"label": "Token buffs", "description": "Cards that buff all tokens (anthems, lords)"},
            {"label": "Token triggers", "description": "Cards that trigger when tokens enter (Impact Tremors)"},
            {"label": "Token value", "description": "Cards that use tokens for sacrifice/value"},
            {"label": "All tokens", "description": "All token-related cards"},
        ],
    },
    "combat_damage": {
        "aliases": ["combat damage", "deals combat damage", "connect", "hits"],
        "question": "What kind of combat damage support?",
        "options": [
            {"label": "Damage triggers", "description": "Cards that trigger when a creature deals combat damage to a player"},
            {"label": "Evasion", "description": "Cards that give evasion to connect (unblockable, flying, trample)"},
            {"label": "Damage multipliers", "description": "Cards that double or increase combat damage"},
            {"label": "All combat damage", "description": "All combat damage synergy cards"},
        ],
    },
}


def check_for_effect_clarification(prompt: str) -> dict | None:
    """
    Check if a prompt is about a specific mechanical effect that needs clarification.
    
    Returns a clarification dict if yes, None if the prompt is clear enough
    to proceed without asking.
    
    Does NOT trigger for:
    - General category requests ("suggest ramp", "need removal")
    - Already-specific requests ("suggest equipment that grants trample under 3 mana")
    - Non-suggest intents (cuts, analyze, swap)
    """
    prompt_lower = prompt.lower().strip()

    # Don't clarify if the prompt is already very specific (long + detailed)
    if len(prompt_lower.split()) >= 8:
        return None

    # Don't clarify if the user has action words — they've already refined
    action_words = [
        "suggest", "find", "recommend", "show", "list", "give",
        "need", "want", "looking for", "search", "get me",
    ]
    if any(word in prompt_lower for word in action_words):
        return None

    # Don't clarify if this IS a clarification response (user already refined)
    # Clarification responses tend to be descriptive phrases starting with
    # "equipment", "cards that trigger", "free sacrifice", etc.
    clarification_indicators = [
        "equipment", "auras that", "spells that", "creatures that trigger",
        "cards that trigger", "free sacrifice", "token generator",
        "cards that return", "cards that put", "all cards that",
        "all ", "directly", "repeatedly", "grant ", "place ",
    ]
    if any(prompt_lower.startswith(indicator) for indicator in clarification_indicators):
        return None

    # Also skip if the prompt matches any known clarification option label or description
    all_option_texts = set()
    for config in SYNERGY_MECHANICS.values():
        for opt in config["options"]:
            all_option_texts.add(opt["label"].lower())
            all_option_texts.add(opt["description"].lower())
    if prompt_lower in all_option_texts:
        return None

    # ── Check for keyword ability grant/need patterns ────────
    for keyword in KEYWORD_ABILITIES:
        if keyword not in prompt_lower:
            continue

        # Detect grant/give/need intent
        grant_patterns = [
            rf'\b(?:give|gives|grant|grants|provide|provides)\b.*\b{keyword}\b',
            rf'\b{keyword}\b.*\b(?:give|gives|grant|grants)\b',
            rf'\b(?:need|needs|wants?|make|makes)\b.*\b{keyword}\b',
            rf'\bcards?\s+(?:that|with|to)\s+.*{keyword}',
            rf'\b{keyword}\b.*\bfor\s+(?:my|the|a)\b',
            rf'\bmy\s+\w+\s+(?:needs?|to have)\s+{keyword}',
        ]

        has_grant_intent = any(re.search(p, prompt_lower) for p in grant_patterns)

        if has_grant_intent:
            return {
                "needs_clarification": True,
                "clarification_question": f"What kind of {keyword} cards are you looking for?",
                "clarification_options": [
                    {"label": f"Grant {keyword}", "description": f"Equipment and auras that grant {keyword} to a creature"},
                    {"label": f"Spells with {keyword}", "description": f"Instant/sorcery spells that give creatures {keyword}"},
                    {"label": f"Creatures with {keyword}", "description": f"Creatures that naturally have {keyword}"},
                    {"label": f"All {keyword} cards", "description": f"All cards that mention {keyword}"},
                ],
                "summary": None,
                "suggestions": [],
                "cuts": [],
                "strategy_notes": None,
                "_clarification_type": "keyword_grant",
                "_keyword": keyword,
            }

    # ── Check for synergy mechanic patterns ──────────────────
    for mechanic, config in SYNERGY_MECHANICS.items():
        matched = False
        for alias in config["aliases"]:
            if alias in prompt_lower:
                matched = True
                break

        if not matched:
            continue

        # Detect synergy/benefit/interact intent
        synergy_patterns = [
            r'\b(?:benefit|benefits|synerg|interact|care|trigger|use|leverage)\b',
            r'\b(?:that|which)\s+(?:benefit|synerg|interact|care|trigger)\b',
            r'\b(?:work with|goes with|pairs with|combo with)\b',
        ]

        has_synergy_intent = any(re.search(p, prompt_lower) for p in synergy_patterns)

        # Also trigger for bare mechanic mentions that are short prompts
        is_short = len(prompt_lower.split()) <= 5

        if has_synergy_intent or is_short:
            return {
                "needs_clarification": True,
                "clarification_question": config["question"],
                "clarification_options": config["options"],
                "summary": None,
                "suggestions": [],
                "cuts": [],
                "strategy_notes": None,
                "_clarification_type": "synergy",
                "_mechanic": mechanic,
            }

    return None