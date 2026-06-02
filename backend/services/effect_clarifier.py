"""
Effect Clarifier — Intent-Based

Detects when a user's prompt is about a specific mechanical effect
and offers clarification options based on INTENT, not card type.

Card type filtering is handled separately by the UI filter system.
This module only cares about: what is the user trying to accomplish?

Runs BEFORE any AI calls or Scryfall searches — pure pattern matching.
"""

import re

# MTG keyword abilities that commonly need intent clarification
KEYWORD_ABILITIES = [
    "trample", "flying", "hexproof", "indestructible", "haste",
    "deathtouch", "lifelink", "vigilance", "menace", "double strike",
    "first strike", "reach", "flash", "ward", "shroud",
    "unblockable", "infect", "wither",
]

# Intent-based clarification for keyword abilities
# Each keyword gets options based on what the user might be trying to DO
def _build_keyword_options(keyword: str) -> list[dict]:
    """Build intent-based clarification options for a keyword ability."""
    return [
        {
            "label": f"Grant {keyword}",
            "description": f"Cards that give {keyword} to my creatures (equipment, auras, spells, enchantments — any card type)",
        },
        {
            "label": f"Creatures with {keyword}",
            "description": f"Creatures that naturally have {keyword}",
        },
        {
            "label": f"Interact with {keyword}",
            "description": f"Cards that benefit from, trigger off, or synergize with {keyword} damage or effects",
        },
        {
            "label": f"All {keyword} cards",
            "description": f"Everything that mentions {keyword} — grant, have, or interact with",
        },
    ]


# Mechanics that have synergy/intent patterns
SYNERGY_MECHANICS = {
    "lifegain": {
        "aliases": ["life gain", "lifegain", "gaining life", "gain life", "lifelink"],
        "question": "What's the goal with lifegain?",
        "options": [
            {"label": "Lifegain payoffs", "description": "Cards that trigger or reward me whenever I gain life (Ajani's Pridemate, Well of Lost Dreams, Archangel of Thune)"},
            {"label": "Lifegain sources", "description": "Cards that gain me life (lifelink creatures, life gain spells, Soul Warden effects)"},
            {"label": "Life as a resource", "description": "Cards that spend or leverage high life totals (Aetherflux Reservoir, Bolas's Citadel, Necropotence)"},
            {"label": "All lifegain", "description": "Everything related to gaining, spending, or benefiting from life"},
        ],
    },
    "sacrifice": {
        "aliases": ["sacrifice", "sacrificing", "sac outlet", "sac"],
        "question": "What's the goal with sacrifice?",
        "options": [
            {"label": "Sacrifice outlets", "description": "Cards that let me sacrifice creatures for free or cheap (Viscera Seer, Ashnod's Altar, Goblin Bombardment)"},
            {"label": "Death payoffs", "description": "Cards that reward me when creatures die (Blood Artist, Zulaport Cutthroat, Grave Pact)"},
            {"label": "Sacrifice fodder", "description": "Cards that create expendable tokens or creatures to sacrifice"},
            {"label": "Recursion after sacrifice", "description": "Cards that bring creatures back after they die to sacrifice again"},
            {"label": "All sacrifice", "description": "Everything sacrifice-related — outlets, payoffs, fodder, and recursion"},
        ],
    },
    "counters": {
        "aliases": ["+1/+1 counter", "counters", "+1 counter", "counter synergy"],
        "question": "What's the goal with +1/+1 counters?",
        "options": [
            {"label": "Place counters", "description": "Cards that put +1/+1 counters on my creatures"},
            {"label": "Counter payoffs", "description": "Cards that trigger or scale when counters are placed (Hardened Scales, Branching Evolution)"},
            {"label": "Proliferate and multiply", "description": "Cards that proliferate, double, or multiply existing counters"},
            {"label": "All counters", "description": "Everything related to +1/+1 counters"},
        ],
    },
    "graveyard": {
        "aliases": ["graveyard", "graveyard synergy", "from the graveyard"],
        "question": "What's the goal with the graveyard?",
        "options": [
            {"label": "Reanimate creatures", "description": "Cards that return creatures from graveyard to battlefield"},
            {"label": "Fill the graveyard", "description": "Self-mill, discard outlets, and cards that stock the graveyard"},
            {"label": "Cast from graveyard", "description": "Flashback, escape, retrace — play spells from the graveyard"},
            {"label": "Graveyard hate", "description": "Exile opponents' graveyards to shut down their strategies"},
            {"label": "All graveyard", "description": "Everything graveyard-related"},
        ],
    },
    "tokens": {
        "aliases": ["token", "tokens", "token generation", "create tokens"],
        "question": "What's the goal with tokens?",
        "options": [
            {"label": "Token generators", "description": "Cards that create creature tokens, especially repeatable sources"},
            {"label": "Token payoffs", "description": "Cards that buff tokens or trigger when tokens enter (anthems, Impact Tremors, Divine Visitation)"},
            {"label": "Token value", "description": "Cards that use tokens as a resource — sacrifice, convoke, populate"},
            {"label": "All tokens", "description": "Everything token-related — generate, buff, and use"},
        ],
    },
    "combat_damage": {
        "aliases": ["combat damage", "deals combat damage", "connect", "hits"],
        "question": "What's the goal with combat damage?",
        "options": [
            {"label": "Damage triggers", "description": "Cards that trigger when a creature deals combat damage to a player"},
            {"label": "Evasion", "description": "Cards that help creatures connect — unblockable, flying, trample, menace"},
            {"label": "Damage multipliers", "description": "Cards that double, extra combat, or increase damage dealt"},
            {"label": "All combat damage", "description": "Everything related to dealing and benefiting from combat damage"},
        ],
    },
    "blink": {
        "aliases": ["blink", "flicker", "exile and return"],
        "question": "What's the goal with blink/flicker?",
        "options": [
            {"label": "Blink enablers", "description": "Cards that exile and return creatures to retrigger ETB effects"},
            {"label": "ETB payoffs", "description": "Creatures with powerful enter-the-battlefield abilities to blink repeatedly"},
            {"label": "All blink", "description": "Everything related to blinking and flickering"},
        ],
    },
    "mill": {
        "aliases": ["mill", "milling", "mill opponents"],
        "question": "What's the goal with mill?",
        "options": [
            {"label": "Mill opponents", "description": "Cards that put opponents' cards from library into graveyard"},
            {"label": "Mill payoffs", "description": "Cards that benefit when cards are milled (Bruvac, Sphinx's Tutelage, Consuming Aberration)"},
            {"label": "Self-mill", "description": "Cards that mill yourself for graveyard synergies"},
            {"label": "All mill", "description": "Everything mill-related"},
        ],
    },
}


def check_for_effect_clarification(prompt: str) -> dict | None:
    """
    Check if a prompt is about a specific mechanical effect that needs
    intent clarification.
    
    Returns a clarification dict if the prompt is ambiguous about intent.
    Returns None if the prompt is clear enough to proceed.
    
    Does NOT trigger for:
    - General category requests ("suggest ramp", "need removal")
    - Already-specific requests (8+ words with clear detail)
    - Rewritten clarification responses from the frontend
    """
    prompt_lower = prompt.lower().strip()

    # Don't clarify if the prompt is already very specific (long + detailed)
    if len(prompt_lower.split()) >= 8:
        return None

    # Don't clarify if this is a rewritten clarification response from the frontend
    if re.search(r'^suggest\s+.+\s+for\s+\w+$', prompt_lower):
        return None

    # Don't clarify if this IS a clarification response (user already refined)
    clarification_indicators = [
        "equipment", "auras that", "spells that", "creatures that trigger",
        "cards that trigger", "free sacrifice", "token generator",
        "cards that return", "cards that put", "all cards that",
        "all ", "directly", "repeatedly", "grant ", "place ",
        "everything", "reanimate", "evasion", "damage trigger",
        "damage multiplier", "blink enabler", "etb payoff",
        "mill opponent", "self-mill", "mill payoff",
    ]
    if any(prompt_lower.startswith(indicator) for indicator in clarification_indicators):
        return None

    # Also skip if the prompt matches any known option description
    all_option_texts = set()
    for config in SYNERGY_MECHANICS.values():
        for opt in config["options"]:
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
                "clarification_question": f"What's the goal with {keyword}?",
                "clarification_options": _build_keyword_options(keyword),
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