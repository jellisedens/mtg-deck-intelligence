"""
Scryfall Oracle Tags — Production Reference
Built from bulk Oracle Tags file (17MB, 35,547 cards, 4,348 unique tags)
Last verified: June 2026

Usage:
  1. Download oracle tags bulk file -> build oracle_id -> [tags] index
  2. AI classifies user prompt -> returns category keys
  3. Match category keys to tag groups below
  4. Filter cards by matching tags
  5. Oracle text fallback for untagged cards
"""

# Maps user-facing categories to actual bulk file tag names
# Built from real card data analysis, not guesswork
CATEGORY_TAG_GROUPS = {
    # === RAMP ===
    "ramp": [
        "ramp", "ramp with set's mechanic",
        "mana rock", "mana rock with set's mechanic", "utility mana rock",
        "mana dork", "mana dork egg", "mana egg",
        "land ramp", "multi land ramp",
        "adds multiple mana",
        "mana producer", "mana increaser", "mana storage",
        "mana filter", "mana fix",
        "repeatable treasures",
    ],
    "mana_rocks": [
        "mana rock", "mana rock with set's mechanic", "utility mana rock",
    ],
    "mana_dorks": [
        "mana dork", "mana dork egg",
    ],
    "land_ramp": [
        "land ramp", "multi land ramp",
        "tutor-land-basic", "tutor-land-to-battlefield",
    ],
    "cost_reducers": [
        "cost-reducer-colored-mana",
    ],

    # === REMOVAL ===
    "removal": [
        "spot removal", "repeatable removal", "multi removal", "swap removal",
        "removal-exile", "removal-destroy", "removal-bounce", "removal-tuck",
        "removal-creature", "removal-permanent", "removal-nonland",
        "removal-artifact", "removal-enchantment", "removal-planeswalker",
        "removal-land", "removal-noncreature", "removal-token",
        "removal-sacrifice", "removal-toughness", "removal-fight",
        "removal-aura", "removal-equipment", "removal-vehicle",
        "removal-battle", "removal-nonenchantment",
    ],
    "spot_removal": [
        "spot removal", "removal-exile", "removal-destroy",
        "removal-creature", "removal-permanent",
        "single target instant/sorcery",
    ],
    "board_wipe": [
        "sweeper", "sweeper-one-sided", "sweeper-graveyard",
        "board-reset", "counterspell-sweeper",
    ],
    "artifact_removal": [
        "removal-artifact",
    ],
    "enchantment_removal": [
        "removal-enchantment", "removal-aura",
    ],

    # === CARD DRAW ===
    "draw": [
        "draw engine", "repeatable pure draw", "pure draw", "burst draw",
        "repeatable draw", "repeatable impulsive draw", "impulsive draw",
        "long term impulsive draw", "extra draw step",
        "hand-positive", "hand-neutral", "egg",
        "drawlink", "gives drawlink",
        "life for cards",
    ],
    "cantrip": [
        "pure draw", "hand-neutral", "egg",
    ],
    "impulse_draw": [
        "impulsive draw", "repeatable impulsive draw", "long term impulsive draw",
    ],
    "wheel": [
        "draw to seven",
    ],
    "loot": [
        "repeatable draw",
    ],

    # === INTERACTION ===
    "counterspell": [
        "counterspell", "counterspell with set mechanic",
        "counterspell-noncreature", "counterspell-creature",
        "counterspell-instant", "counterspell-sorcery",
        "counterspell-enchantment", "counterspell-artifact",
        "counterspell-planeswalker", "counterspell-aura",
        "counterspell-battle",
        "counterspell-free", "counterspell-soft",
        "counterspell-bounce", "counterspell-exile",
        "counterspell-sacrifice", "counterspell-tuck",
        "counterspell-reusable", "counterspell-automatic",
        "counterspell-loyalty-ability", "counterspell-ability",
    ],
    "bounce": [
        "removal-bounce",
    ],

    # === PROTECTION ===
    "protection": [
        "protects-creature", "protects-permanent", "protects-all",
        "protects-land", "protects-artifact", "protects-enchantment",
        "protects-planeswalker", "protects-nonland", "protects-vehicle",
        "gives hexproof", "gives indestructible", "gives shroud",
        "gives protection", "gives ward",
        "gives player hexproof", "gives player protection", "gives player shroud",
        "wrath-protection",
        "circle of protection",
    ],
    "evasion": [
        "gives flying", "gives trample", "gives menace",
        "gives unblockable", "gives skulk", "gives shadow",
        "gives horsemanship", "gives fear", "gives intimidate",
        "gives forestwalk", "gives islandwalk", "gives mountainwalk",
        "gives plainswalk", "gives swampwalk", "gives landwalk",
        "gives evasion", "evasion",
    ],
    "haste_enabler": [
        "gives haste", "gives super haste",
    ],
    "flash_enabler": [
        "gives flash",
    ],

    # === LIFEGAIN ===
    "lifegain": [
        "lifegain", "repeatable lifegain", "soul warden ability",
        "gives lifelink", "gains lifelink", "old lifelink",
        "lifegain increaser", "life doubler",
        "opponent lifegain",
    ],
    "lifegain_payoff": [
        "lifegain matters", "pridemate", "super-pridemate",
        "life-total-matters-self", "lifegain to damage",
    ],
    "drain": [
        "blood artist ability",
    ],

    # === GRAVEYARD ===
    "recursion": [
        "mass reanimation",
    ],
    "graveyard_hate": [
        "sweeper-graveyard",
    ],

    # === SACRIFICE ===
    "sacrifice": [
        "sacrifice outlet", "sacrifice outlet-creature",
        "sacrifice outlet-artifact", "sacrifice outlet-enchantment",
        "sacrifice outlet-land", "sacrifice outlet-permanent",
        "sacrifice outlet-planeswalker", "sacrifice outlet-token",
        "sacrifice outlet-nonland",
        "free sacrifice outlet", "repeatable sacrifice outlet",
    ],
    "death_triggers": [
        "death trigger", "death trigger-self", "death trigger opponent",
        "blood artist ability", "grave pact",
    ],

    # === TUTOR ===
    "tutor": [
        "tutor-card", "tutor-to-hand", "tutor-to-top",
        "tutor-to-battlefield", "tutor-to-graveyard", "tutor-to-exile",
        "tutor-creature", "tutor-artifact", "tutor-enchantment",
        "tutor-instant", "tutor-sorcery", "tutor-planeswalker",
        "tutor-land-any", "tutor-land-basic",
        "tutor-land-to-battlefield",
        "tutor-artifact-equipment", "tutor-enchantment-aura",
        "tutor-legendary", "tutor-permanent", "tutor-nonland",
        "tutor-noncreature", "tutor-self",
        "tutor-cast", "tutor-flash",
    ],

    # === TOKENS ===
    "tokens": [
        "repeatable creature tokens",
    ],
    "anthem": [
        "gives pp counters to all", "gives pp counters",
    ],

    # === COMBAT ===
    "combat_trick": [
        "combat trick",
    ],
    "attack_triggers": [
        "attack trigger", "attacking matters-self",
    ],

    # === MULTIPLAYER ===
    "group_slug": [
        "group slug",
    ],

    # === STAX ===
    "stax": [
        "hatebear", "cast tax", "silence",
        "prevent activation", "hate-flash",
        "kismet effect",
    ],

    # === BURN ===
    "burn": [
        "burn any", "burn creature", "burn player", "burn planeswalker",
        "bombard",
    ],
}

# Oracle text fallback patterns for cards without tags
ORACLE_FALLBACKS = {
    "ramp": ["{T}: Add {C}{C}", "{T}: Add {", "search your library for a basic land", "additional land", "add one mana", "add two mana", "add three mana"],
    "mana_rocks": ["add {", "{T}: Add"],
    "mana_dorks": ["add {", "{T}: Add"],
    "land_ramp": ["search your library for a basic land", "land onto the battlefield"],
    "cost_reducers": ["cost", "less to cast", "costs {"],
    "removal": ["destroy target", "exile target", "deals damage to target"],
    "spot_removal": ["destroy target", "exile target"],
    "board_wipe": ["destroy all", "exile all", "all creatures get -", "each creature gets -"],
    "artifact_removal": ["destroy target artifact", "exile target artifact"],
    "enchantment_removal": ["destroy target enchantment", "exile target enchantment"],
    "draw": ["draw a card", "draw cards", "draw two", "draw three"],
    "cantrip": ["draw a card"],
    "impulse_draw": ["exile the top", "you may play", "you may cast"],
    "wheel": ["each player discards", "discard your hand"],
    "counterspell": ["counter target spell", "counter target"],
    "bounce": ["return target", "to its owner's hand"],
    "protection": ["hexproof", "indestructible", "shroud", "protection from"],
    "evasion": ["can't be blocked", "flying", "trample", "menace"],
    "haste_enabler": ["haste"],
    "flash_enabler": ["flash", "as though they had flash"],
    "lifegain": ["gain life", "gains life", "lifelink"],
    "lifegain_payoff": ["whenever you gain life", "life you gained"],
    "drain": ["each opponent loses", "opponent loses life"],
    "sacrifice": ["sacrifice a creature", "sacrifice a permanent", "sacrifice another"],
    "death_triggers": ["when", "dies", "whenever a creature dies"],
    "tutor": ["search your library"],
    "tokens": ["create a", "token", "create"],
    "anthem": ["creatures you control get +"],
    "burn": ["deals damage", "damage to any target", "damage to target"],
    "stax": ["can't", "don't untap", "costs more to cast"],
    "group_slug": ["each player", "each opponent", "deals damage to each"],
    "recursion": ["return target", "from your graveyard", "to the battlefield"],
    "graveyard_hate": ["exile target card from a graveyard", "exile all cards from"],
    "attack_triggers": ["whenever", "attacks"],
    "combat_trick": ["gets +", "until end of turn"],
}

# Categories available for the AI classifier
AVAILABLE_CATEGORIES = list(CATEGORY_TAG_GROUPS.keys())