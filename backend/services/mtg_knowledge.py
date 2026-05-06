"""
MTG Game Knowledge Base

Codified expert knowledge about Magic: The Gathering deckbuilding.
Used by:
- AI planner (_get_ai_plan) for better Scryfall query generation
- Playbook generator (future) for archetype-specific guidance
- Suggest prompts for format-aware recommendations

This is reference data, not business logic. Expand it as gaps are discovered.
"""


# ─── Format Heuristics ────────────────────────────────
# Target ranges for deck composition by format.
# Used to evaluate whether a deck is balanced and what it needs.

FORMAT_HEURISTICS = {
    "commander": {
        "total_cards": 100,
        "land_range": [35, 38],
        "ramp_range": [10, 15],
        "card_draw_range": [10, 15],
        "removal_range": [5, 8],
        "board_wipe_range": [2, 4],
        "protection_range": [2, 4],
        "tutor_range": [2, 5],
        "win_condition_range": [3, 6],
        "notes": [
            "Singleton format — exactly 1 copy of each card except basic lands",
            "Commander tax increases by {2} each time commander is recast",
            "High-CMC commanders (6+) need 12+ ramp sources to reliably cast by turn 5",
            "Color fixing is critical in 3+ color decks — budget for 5+ dual/tri lands",
            "Average CMC above 3.5 signals a deck that needs heavy ramp investment",
            "Multiplayer games run longer — card advantage and resilience matter more than raw speed",
        ],
    },
    "standard": {
        "total_cards": 60,
        "land_range": [22, 26],
        "notes": [
            "Small card pool — build around what's available in current sets",
            "Games are faster — curve should peak at 2-3 CMC for aggro, 3-4 for midrange",
            "Redundancy matters since you can run 4 copies of key cards",
            "Sideboard (15 cards) is critical for best-of-three matches",
        ],
    },
    "modern": {
        "total_cards": 60,
        "land_range": [20, 24],
        "notes": [
            "Fast format — need interaction by turn 2-3 or a proactive game plan",
            "Fetch lands + shock lands are the standard mana base",
            "Graveyard hate is essential in sideboards",
            "Free spells and efficient threats define the format",
        ],
    },
    "pioneer": {
        "total_cards": 60,
        "land_range": [22, 25],
        "notes": [
            "Slower than Modern but faster than Standard",
            "No fetch lands — mana bases rely on shock lands and check lands",
            "Midrange and combo strategies are strong",
        ],
    },
}


# ─── Archetype Templates ─────────────────────────────
# What each archetype typically needs. Used during playbook generation
# to produce deck-specific category guidance.

ARCHETYPE_TEMPLATES = {
    "tribal": {
        "description": "Deck built around a specific creature type with synergy payoffs",
        "key_needs": [
            "Lords/anthems that buff the chosen type",
            "Cost reducers specific to the tribe (e.g., Dragonspeaker Shaman for dragons)",
            "Tribal draw engines (e.g., Kindred Discovery, Beast Whisperer)",
            "Tribal-specific removal or utility (e.g., Crux of Fate for dragons)",
            "Sufficient creature density of the chosen type (usually 25-35)",
            "Support cards that care about creature type (e.g., Coat of Arms, Door of Destinies)",
        ],
        "scryfall_patterns": {
            "tribal_support": "otag:tribal-{type}",
            "lords": "t:creature o:\"{type}\" (o:\"+1/+1\" or o:\"gets\")",
            "cost_reduction": "o:\"{type}\" o:\"cost\" o:\"less\"",
            "tribal_draw": "o:\"{type}\" o:\"draw\"",
            "type_specific": "t:{type}",
        },
        "common_pitfalls": [
            "Too many high-CMC tribe members without enough ramp",
            "Not enough non-creature support (removal, draw, protection)",
            "Over-reliance on commander — need the deck to function without it",
        ],
    },
    "spellslinger": {
        "description": "Deck focused on casting many instants and sorceries for value",
        "key_needs": [
            "Cantrips and cheap draw spells to maintain velocity",
            "Copy effects to double up on key spells",
            "Payoffs for casting instants/sorceries (e.g., Guttersnipe, Talrand)",
            "Storm or storm-adjacent finishers",
            "Mana rocks over land ramp (instant-speed mana helps)",
            "Recursion to rebuy key spells from graveyard",
        ],
        "scryfall_patterns": {
            "payoffs": "o:\"whenever you cast\" (o:\"instant\" or o:\"sorcery\")",
            "cantrips": "(t:instant or t:sorcery) o:\"draw\" cmc<=2",
            "copy": "o:\"copy\" o:\"spell\"",
            "recursion": "o:\"return\" o:\"instant\" o:\"graveyard\"",
        },
        "common_pitfalls": [
            "Too few creatures to close out the game",
            "Running out of cards without enough draw",
            "Vulnerable to counterspells since the whole plan is spell-based",
        ],
    },
    "reanimator": {
        "description": "Deck that fills the graveyard and brings back powerful creatures",
        "key_needs": [
            "Self-mill and discard outlets to fill graveyard",
            "Reanimation spells (Reanimate, Animate Dead, Living Death)",
            "High-impact reanimation targets (big creatures with ETB/attack triggers)",
            "Graveyard protection (avoid exile effects)",
            "Backup plan if graveyard gets exiled",
        ],
        "scryfall_patterns": {
            "reanimate": "o:\"return\" o:\"creature\" o:\"graveyard\" o:\"battlefield\"",
            "self_mill": "o:\"mill\" or (o:\"put\" o:\"cards\" o:\"graveyard\")",
            "discard_outlets": "o:\"discard\" o:\"card\"",
            "targets": "t:creature cmc>=6 (o:\"when\" or o:\"whenever\")",
        },
        "common_pitfalls": [
            "No backup plan when graveyard is exiled",
            "Too many reanimation targets, not enough enablers",
            "Insufficient interaction to survive until reanimation turns online",
        ],
    },
    "voltron": {
        "description": "Deck focused on making one creature (usually commander) lethal",
        "key_needs": [
            "Equipment and auras that grant evasion, protection, and power",
            "Haste enablers to attack immediately after suiting up",
            "Protection for the equipped creature (hexproof, indestructible, ward)",
            "Equipment tutors (Stoneforge Mystic, Open the Armory)",
            "Low-cost equip costs or free-equip effects",
        ],
        "scryfall_patterns": {
            "equipment": "t:equipment",
            "auras": "t:aura o:\"enchanted creature gets\"",
            "protection": "(o:\"hexproof\" or o:\"indestructible\" or o:\"shroud\")",
            "equip_tutors": "o:\"search\" o:\"equipment\"",
        },
        "common_pitfalls": [
            "All-in on one creature with no recovery plan",
            "Equipment too expensive to cast and equip in same turn",
            "No evasion — big creature gets chump-blocked forever",
        ],
    },
    "aristocrats": {
        "description": "Deck that sacrifices creatures for value and drains opponents",
        "key_needs": [
            "Sacrifice outlets (free sac is best — Viscera Seer, Ashnod's Altar)",
            "Death triggers (Blood Artist, Zulaport Cutthroat)",
            "Token generators for sacrifice fodder",
            "Recursion to rebuy sacrificed creatures",
            "Card draw tied to creatures dying",
        ],
        "scryfall_patterns": {
            "sac_outlets": "o:\"sacrifice a creature\" (o:\"add\" or o:\"draw\" or o:\"scry\")",
            "death_triggers": "o:\"whenever\" o:\"creature\" o:\"dies\"",
            "token_fodder": "o:\"create\" o:\"token\" o:\"creature\"",
            "recursion": "o:\"return\" o:\"creature\" o:\"graveyard\"",
        },
        "common_pitfalls": [
            "Too few sacrifice outlets — plan doesn't function",
            "No free sac outlets — paying mana to sacrifice is too slow",
            "Token generators too expensive — need cheap/repeatable fodder",
        ],
    },
    "control": {
        "description": "Deck that answers threats and wins in the late game",
        "key_needs": [
            "Counterspells and removal to answer threats",
            "Board wipes to reset when behind",
            "Card draw engines to maintain advantage",
            "Win conditions that are hard to interact with",
            "Mana rocks for early acceleration into answers",
        ],
        "scryfall_patterns": {
            "counters": "o:\"counter target spell\" t:instant",
            "removal": "(o:\"destroy target\" or o:\"exile target\") t:instant",
            "board_wipes": "o:\"destroy all\" (t:sorcery or t:instant)",
            "draw_engines": "t:enchantment o:\"draw a card\"",
        },
        "common_pitfalls": [
            "Too few win conditions — controls the game but can't close it",
            "Answers don't match the meta — wrong removal for the threats you face",
            "Running out of cards trying to answer everything",
        ],
    },
    "combo": {
        "description": "Deck built around assembling specific card combinations to win",
        "key_needs": [
            "Combo pieces (redundancy helps — multiple cards that fill each slot)",
            "Tutors to find combo pieces reliably",
            "Protection to resolve the combo (counterspell backup, Grand Abolisher)",
            "Card draw/selection to dig for pieces",
            "Backup combos in case primary is disrupted",
        ],
        "scryfall_patterns": {
            "tutors": "o:\"search your library\"",
            "protection": "o:\"can't be countered\" or o:\"opponents can't cast\"",
            "selection": "o:\"look at the top\" o:\"put\"",
        },
        "common_pitfalls": [
            "Only one combo line with no backup",
            "No protection — combo gets countered and there's no plan B",
            "Too many combo pieces, not enough interaction to survive",
        ],
    },
    "tokens": {
        "description": "Deck that creates many creature tokens and overwhelms with numbers",
        "key_needs": [
            "Token generators (repeatable sources are best)",
            "Anthems and lords to buff tokens (+1/+1 effects)",
            "Sacrifice synergies (tokens are great sacrifice fodder)",
            "Finishers (Craterhoof Behemoth, Triumph of the Hordes)",
            "Protection from board wipes (Teferi's Protection, Heroic Intervention)",
        ],
        "scryfall_patterns": {
            "generators": "o:\"create\" o:\"creature token\"",
            "anthems": "o:\"creatures you control get +\"",
            "finishers": "o:\"creatures you control\" (o:\"trample\" or o:\"+X/+X\")",
        },
        "common_pitfalls": [
            "Tokens die to a single board wipe with no recovery",
            "No anthem effects — 1/1 tokens don't pressure opponents",
            "Too slow — not enough early token generation",
        ],
    },
    "landfall": {
        "description": "Deck that triggers abilities when lands enter the battlefield",
        "key_needs": [
            "Extra land drop effects (Azusa, Exploration, Oracle of Mul Daya)",
            "Landfall payoffs (Avenger of Zendikar, Omnath, Rampaging Baloths)",
            "Land tutors and fetch effects to trigger landfall multiple times",
            "Ways to return lands from graveyard to hand/battlefield",
            "Card draw to keep the land drops coming",
        ],
        "scryfall_patterns": {
            "extra_drops": "o:\"additional land\" or o:\"play an additional land\"",
            "payoffs": "o:\"whenever a land enters the battlefield under your control\"",
            "fetch": "o:\"search your library\" o:\"land\" o:\"battlefield\"",
            "land_recursion": "o:\"return\" o:\"land\" o:\"graveyard\"",
        },
        "common_pitfalls": [
            "Running out of lands in hand — need draw to sustain",
            "Too many payoffs, not enough enablers (extra land drops)",
            "Vulnerable when board is wiped since rebuilding requires land drops",
        ],
    },
    "stax": {
        "description": "Deck that restricts opponents' actions through taxing and denial",
        "key_needs": [
            "Tax effects (Rhystic Study, Smothering Tithe, Thalia)",
            "Resource denial (Winter Orb, Static Orb, Stasis)",
            "Asymmetric effects that hurt opponents more than you",
            "A win condition that works under your own restrictions",
            "Mana rocks to function while lands are locked down",
        ],
        "scryfall_patterns": {
            "tax": "o:\"unless\" o:\"pays\" or o:\"costs\" o:\"more\"",
            "denial": "o:\"don't untap\" or o:\"can't\" o:\"more than\"",
            "asymmetric": "o:\"each opponent\" (o:\"sacrifice\" or o:\"discard\")",
        },
        "common_pitfalls": [
            "Locking yourself out with symmetric effects",
            "No win condition — the game stalls forever",
            "Becoming the archenemy — stax draws a lot of hate in multiplayer",
        ],
    },
}


# ─── Scryfall Advanced Syntax Guide ──────────────────
# Reference for the AI planner when building complex queries.

SCRYFALL_SYNTAX_GUIDE = """
ADVANCED SCRYFALL QUERY SYNTAX:

Oracle Tags (community-maintained, highly reliable):
- otag:tribal-dragon — cards tagged as dragon tribal support
- otag:tribal-elf, otag:tribal-goblin, etc. — tribal support for any creature type
- otag:ramp — cards tagged as mana ramp
- otag:removal — cards tagged as removal
- otag:draw — cards tagged as card draw
- Combine tags: otag:tribal-dragon otag:ramp — dragon-specific ramp cards
- These are curated by the Scryfall community and are MORE RELIABLE than oracle text searches for finding role-specific cards

Color Identity (for Commander):
- id<=WUBRG — color identity is within these colors (use for Commander)
- id:WUBRG — color identity is exactly these colors
- c:red — card color is red (different from color identity)
- ALWAYS use id<= for Commander format, never c:

Type and Subtype:
- t:creature — type contains creature
- t:dragon — subtype contains dragon
- t:legendary — supertype contains legendary
- t:"legendary creature" — both legendary and creature

Oracle Text:
- o:"destroy target" — exact phrase in oracle text
- o:dragon o:cost o:less — all three words appear (not necessarily together)
- Combine with types: t:creature o:"add" — creatures that add mana

Format Legality:
- f:commander — legal in Commander
- f:modern — legal in Modern
- f:standard — legal in Standard

Mana Cost and CMC:
- cmc<=3 — converted mana cost 3 or less
- cmc=0 — zero cost (free spells)
- mana:{W}{W} — exact mana cost

Power/Toughness:
- pow>=5 — power 5 or greater
- tou>=4 — toughness 4 or greater

Price:
- usd<1 — under $1
- usd>=10 — $10 or more

EDHREC Rank:
- Results sorted by EDHREC rank by default — lower rank = more popular in Commander

QUERY STRATEGY:
- Generate 4-6 queries per request covering different angles
- Always include at least one broad fallback query that guarantees results
- Mix specific otag queries with oracle text searches
- For tribal requests, ALWAYS include: otag:tribal-{type} as one query
- For role requests in tribal decks, combine: otag:tribal-{type} otag:{role}
- Prefer multiple focused queries over one complex query
"""


# ─── Category Definitions ────────────────────────────
# Maps category names to their functional definitions.
# Used to help the AI understand what a category means beyond the keyword.

CATEGORY_DEFINITIONS = {
    "ramp": {
        "definition": "Cards that accelerate mana production beyond natural land drops",
        "subcategories": [
            "Mana dorks — creatures that tap for mana",
            "Mana rocks — artifacts that produce mana",
            "Land ramp — spells that search for lands and put them onto the battlefield",
            "Cost reducers — cards that make specific spells cheaper",
            "Extra land drops — effects that let you play additional lands per turn",
            "Treasure/temporary mana — one-time mana bursts",
        ],
    },
    "card_draw": {
        "definition": "Cards that increase the number of cards in your hand",
        "subcategories": [
            "Draw engines — repeatable draw effects (enchantments, creatures)",
            "Burst draw — one-time large draw spells",
            "Cantrips — cheap spells that replace themselves",
            "Impulse draw — exile top cards and play them (red draw)",
            "Tutor-adjacent — cards that find specific cards (Vampiric Tutor counts as draw)",
        ],
    },
    "removal": {
        "definition": "Cards that deal with opponents' permanents or spells",
        "subcategories": [
            "Spot removal — destroy or exile a single target",
            "Board wipes — destroy or exile all creatures/permanents",
            "Counterspells — prevent spells from resolving",
            "Damage-based — deal damage to creatures (red removal)",
            "Bounce — return permanents to hand (temporary removal)",
            "Artifact/enchantment removal — specifically handles noncreature permanents",
        ],
    },
    "protection": {
        "definition": "Cards that keep your important permanents alive",
        "subcategories": [
            "Targeted protection — hexproof, indestructible, ward on specific permanents",
            "Board protection — prevent all destruction (Teferi's Protection, Heroic Intervention)",
            "Counterspell backup — counter removal aimed at your things",
            "Recursion-as-protection — bring things back after they die",
        ],
    },
    "win_condition": {
        "definition": "Cards that directly close out the game",
        "subcategories": [
            "Combat damage — large creatures, evasion, anthems",
            "Combo finish — infinite damage, mill, life loss",
            "Commander damage — 21 damage from commander kills a player",
            "Alternative win — Thassa's Oracle, Revel in Riches, etc.",
        ],
    },
}


def get_format_heuristics(format_name: str) -> dict:
    """Get heuristics for a specific format, with commander as default."""
    return FORMAT_HEURISTICS.get(format_name, FORMAT_HEURISTICS["commander"])


def get_archetype_template(archetype: str) -> dict | None:
    """Get template for a specific archetype. Returns None if not found."""
    archetype_lower = archetype.lower().strip()
    
    # Direct match
    if archetype_lower in ARCHETYPE_TEMPLATES:
        return ARCHETYPE_TEMPLATES[archetype_lower]
    
    # Common aliases
    aliases = {
        "aggro": "tribal",
        "dragon tribal": "tribal",
        "elf tribal": "tribal",
        "goblin tribal": "tribal",
        "zombie tribal": "tribal",
        "creature-based": "tribal",
        "sacrifice": "aristocrats",
        "sac": "aristocrats",
        "graveyard": "reanimator",
        "reanimate": "reanimator",
        "spell-based": "spellslinger",
        "instants and sorceries": "spellslinger",
        "equipment": "voltron",
        "aura": "voltron",
        "pillowfort": "control",
        "permission": "control",
        "infinite combo": "combo",
        "go wide": "tokens",
        "token": "tokens",
        "lands matter": "landfall",
        "tax": "stax",
        "hatebears": "stax",
    }
    
    if archetype_lower in aliases:
        return ARCHETYPE_TEMPLATES[aliases[archetype_lower]]
    
    # Partial match
    for key in ARCHETYPE_TEMPLATES:
        if key in archetype_lower or archetype_lower in key:
            return ARCHETYPE_TEMPLATES[key]
    
    return None


def build_knowledge_context(format_name: str, archetype: str = None,
                            creature_type: str = None) -> str:
    """
    Build a compact knowledge context string for injection into AI prompts.
    Includes format heuristics + archetype guidance if available.
    """
    parts = []
    
    # Format heuristics
    fmt = get_format_heuristics(format_name)
    parts.append(f"FORMAT: {format_name}")
    if "land_range" in fmt:
        parts.append(f"  Lands: {fmt['land_range'][0]}-{fmt['land_range'][1]}")
    if "ramp_range" in fmt:
        parts.append(f"  Ramp: {fmt['ramp_range'][0]}-{fmt['ramp_range'][1]} sources")
    if "card_draw_range" in fmt:
        parts.append(f"  Draw: {fmt['card_draw_range'][0]}-{fmt['card_draw_range'][1]} sources")
    if "removal_range" in fmt:
        parts.append(f"  Removal: {fmt['removal_range'][0]}-{fmt['removal_range'][1]} pieces")
    if "board_wipe_range" in fmt:
        parts.append(f"  Board wipes: {fmt['board_wipe_range'][0]}-{fmt['board_wipe_range'][1]}")
    for note in fmt.get("notes", []):
        parts.append(f"  • {note}")
    
    # Archetype guidance
    if archetype:
        template = get_archetype_template(archetype)
        if template:
            parts.append(f"\nARCHETYPE: {archetype}")
            parts.append(f"  {template['description']}")
            parts.append("  Key needs:")
            for need in template["key_needs"]:
                parts.append(f"    • {need}")
            parts.append("  Common pitfalls:")
            for pitfall in template["common_pitfalls"]:
                parts.append(f"    ✗ {pitfall}")
    
    # Tribal-specific Scryfall hints
    if creature_type and archetype:
        template = get_archetype_template(archetype)
        if template and "scryfall_patterns" in template:
            parts.append(f"\n  Scryfall query hints for {creature_type} {archetype}:")
            for role, pattern in template["scryfall_patterns"].items():
                resolved = pattern.replace("{type}", creature_type.lower())
                parts.append(f"    {role}: {resolved}")
    
    return "\n".join(parts)