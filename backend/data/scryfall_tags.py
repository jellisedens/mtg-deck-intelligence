# Scryfall Tagger Tags — Working Reference
# Last verified: June 2026
# Use with otag: prefix in Scryfall search (e.g., otag:ramp f:commander)

SCRYFALL_TAGS = {
    # === RAMP (2051+ cards) ===
    "ramp": 2051,           # All ramp
    "mana-dork": 394,       # Creatures that tap for mana
    "mana-rock": 340,       # Artifacts that produce mana
    "land-ramp": 572,       # Spells that search for lands
    "cost-reducer": 281,    # Cards that reduce spell costs

    # === REMOVAL (6008+ cards) ===
    "removal": 6008,        # All removal
    "creature-removal": 5122,
    "spot-removal": 4556,
    "artifact-removal": 1088,
    "enchantment-removal": 954,
    "board-wipe": 884,      # Same as boardwipe and mass-removal
    "disenchant": 215,      # Artifact + enchantment removal
    "burn": 2794,           # Damage-based removal

    # === CARD DRAW (3831+ cards) ===
    "draw": 3831,           # All draw effects
    "card-advantage": 5545, # Broader: includes draw + other advantage
    "cantrip": 581,         # Cheap spells that replace themselves
    "impulse-draw": 229,    # Exile top and cast
    "loot": 361,            # Draw then discard
    "wheel": 126,           # Discard hand, draw new

    # === INTERACTION (511+ cards) ===
    "counter": 511,         # Same as counterspell
    "counterspell": 511,
    "bounce": 863,          # Return to hand
    "freeze": 188,          # Tap and don't untap

    # === LIFEGAIN (2356 cards) ===
    "lifegain": 2356,
    "drain-life": 356,      # Opponent loses, you gain

    # === PROTECTION (1218 cards) ===
    "protection": 1218,
    "evasion": 4820,        # Can't be blocked
    "fog": 91,              # Prevent combat damage
    "hatebear": 53,         # Small creatures that disrupt

    # === GRAVEYARD (2066+ cards) ===
    "recursion": 2066,      # Return from graveyard
    "reanimate": 939,       # Put creatures from GY to battlefield
    "graveyard-fuel": 430,  # Put cards into graveyard
    "graveyard-hate": 405,  # Exile graveyards
    "death-trigger": 1482,  # When a creature dies

    # === SACRIFICE (1360+ cards) ===
    "sacrifice-outlet": 1360,
    "free-sac-outlet": 174, # No mana cost to sacrifice

    # === TUTOR (1080 cards) ===
    "tutor": 1080,

    # === TOKENS / CREATURES ===
    "anthem": 390,          # +1/+1 to all your creatures
    "combat-trick": 973,    # Instant-speed combat buffs
    "animate": 578,         # Turn noncreatures into creatures
    "clone": 67,            # Copy creatures
    "copy": 885,            # Copy spells/permanents

    # === BLINK (163 cards) ===
    "blink": 163,           # Same as flicker
    "flicker": 163,
    "flicker-creature": 132,

    # === MILL / DISCARD ===
    "mill": 1153,
    "discard": 536,

    # === MULTIPLAYER ===
    "group-slug": 721,      # Everyone takes damage/punishment
    "group-hug": 373,       # Everyone benefits
    "goad": None,           # Not confirmed but likely works via otag

    # === EXTRA RESOURCES ===
    "extra-land": 148,      # Play additional lands
    "extra-turn": 52,
    "extra-combat-phase": 43,
    "extra-untap": 94,

    # === DAMAGE MULTIPLIERS ===
    "damage-doubler": 44,
    "damage-multiplier": 44,
    "damage-tripler": 44,

    # === OTHER ===
    "attack-trigger": 1908,
    "enchantress": 16,      # Draw when playing enchantments
    "donate": 64,           # Give permanents to opponents
    "alternate-win-condition": 59,
    "gating": 13,           # Return permanent to hand on ETB
}

# === CATEGORY MAPPING ===
# Maps user-facing categories to their otag queries
CATEGORY_TO_TAGS = {
    "ramp": ["ramp"],
    "mana_dorks": ["mana-dork"],
    "mana_rocks": ["mana-rock"],
    "land_ramp": ["land-ramp"],
    "cost_reducers": ["cost-reducer"],
    "removal": ["removal"],
    "spot_removal": ["spot-removal"],
    "board_wipes": ["board-wipe"],
    "artifact_removal": ["artifact-removal"],
    "enchantment_removal": ["enchantment-removal"],
    "card_draw": ["draw"],
    "cantrips": ["cantrip"],
    "impulse_draw": ["impulse-draw"],
    "wheel": ["wheel"],
    "loot": ["loot"],
    "counterspells": ["counterspell"],
    "bounce": ["bounce"],
    "lifegain": ["lifegain"],
    "drain": ["drain-life"],
    "protection": ["protection"],
    "evasion": ["evasion"],
    "fog": ["fog"],
    "tutor": ["tutor"],
    "recursion": ["recursion"],
    "reanimate": ["reanimate"],
    "graveyard_hate": ["graveyard-hate"],
    "sacrifice": ["sacrifice-outlet"],
    "free_sac": ["free-sac-outlet"],
    "death_triggers": ["death-trigger"],
    "attack_triggers": ["attack-trigger"],
    "anthem": ["anthem"],
    "combat_tricks": ["combat-trick"],
    "blink": ["blink"],
    "clone": ["clone"],
    "copy": ["copy"],
    "mill": ["mill"],
    "discard": ["discard"],
    "group_slug": ["group-slug"],
    "group_hug": ["group-hug"],
    "extra_lands": ["extra-land"],
    "extra_turns": ["extra-turn"],
    "extra_combats": ["extra-combat-phase"],
    "damage_doublers": ["damage-doubler"],
    "burn": ["burn"],
    "enchantress": ["enchantress"],
    "alternate_wincon": ["alternate-win-condition"],
    "hatebear": ["hatebear"],
    "animate": ["animate"],
    "freeze": ["freeze"],
}