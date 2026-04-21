"""
Knowledge base for simulation tag generation.
Maps common oracle text patterns to correct mechanical interpretations.
The AI references these patterns when generating sim tags.
"""

SIM_TAG_PATTERNS = """
CRITICAL REFERENCE — CORRECT MECHANICAL TRANSLATIONS:
Use these patterns as authoritative templates when generating sim tags.

=== RAMP SPELLS ===

Pattern: "Search your library for up to two basic land cards, reveal those cards,
and put one onto the battlefield tapped and the other into your hand"
Cards: Cultivate, Kodama's Reach
Correct tags:
  on_resolve: [
    {"action": "search_land", "count": 1, "destination": "battlefield", "enters_tapped": true, "land_type": "basic"},
    {"action": "search_land", "count": 1, "destination": "hand", "land_type": "basic"},
    {"action": "shuffle_library"}
  ]
COMMON MISTAKE: Do NOT put count: 2 to battlefield. One goes to battlefield, one to hand.

Pattern: "Search your library for a Forest card and put that card onto the battlefield"
Cards: Nature's Lore
Correct tags:
  on_resolve: [
    {"action": "search_land", "count": 1, "destination": "battlefield", "enters_tapped": false, "land_type": "forest"},
    {"action": "shuffle_library"}
  ]
NOTE: Nature's Lore puts the land onto the battlefield UNTAPPED.

Pattern: "Search your library for a Plains, Island, Swamp, or Mountain card,
put it onto the battlefield tapped"
Cards: Farseek
Correct tags:
  on_resolve: [
    {"action": "search_land", "count": 1, "destination": "battlefield", "enters_tapped": true, "land_type": "any_nonforest"},
    {"action": "shuffle_library"}
  ]

Pattern: "Search your library for a basic land card, put that card onto the
battlefield tapped"
Cards: Rampant Growth, Sakura-Tribe Elder
Correct tags:
  on_resolve: [
    {"action": "search_land", "count": 1, "destination": "battlefield", "enters_tapped": true, "land_type": "basic"},
    {"action": "shuffle_library"}
  ]

=== LANDS ===

Pattern: "enters the battlefield tapped unless you pay 2 life"
Cards: Stomping Ground, Breeding Pool, Blood Crypt, Temple Garden, Hallowed Fountain,
       Godless Shrine, Sacred Foundry, Steam Vents, Overgrown Tomb, Watery Grave
Correct tags:
  enters_tapped: false (ALWAYS assume pay 2 life in simulation — aggressive mulligan)
  mana_production: {"type": "tap", "produces_choice": ["R", "G"], "produces_any": false, "amount": 1}
COMMON MISTAKE: Do NOT set enters_tapped: true for shock lands.
COMMON MISTAKE: Do NOT use produces: {"R": 1, "G": 1} — use produces_choice since you pick ONE.

Pattern: "enters the battlefield tapped unless you control two or more basic lands"
Cards: Cinder Glade, Canopy Vista, Prairie Stream, Sunken Hollow, Smoldering Marsh
Correct tags:
  enters_tapped: true (conservative — early game you often don't have 2 basics)
  mana_production: {"type": "tap", "produces_choice": ["R", "G"], "produces_any": false, "amount": 1}

Pattern: "{T}: Add one mana of any color" or "any color of mana"
Cards: Command Tower, Exotic Orchard, City of Brass, Mana Confluence
Correct tags:
  mana_production: {"type": "tap", "produces_any": true, "amount": 1}

Pattern: "Choose a creature type" + "{T}: Add one mana of any color. Spend this mana
only to cast a creature spell of the chosen type"
Cards: Unclaimed Territory, Cavern of Souls
Correct tags:
  mana_production: {"type": "tap", "produces_any": true, "amount": 1}
NOTE: For simulation purposes, treat as any-color since the deck is tribal.

Pattern: "{T}: Add {C}" + other activated abilities
Cards: Haven of the Spirit Dragon, Rogue's Passage, Bojuka Bog
Correct tags:
  mana_production: {"type": "tap", "produces": {"C": 1}, "amount": 1}
  (additional abilities go in static_effects or on_etb as appropriate)

=== MANA ROCKS ===

Pattern: "{T}: Add {C}{C}"
Cards: Sol Ring
Correct tags:
  mana_production: {"type": "tap", "produces": {"C": 2}, "amount": 2}

Pattern: "{T}: Add one mana of any color in your commander's color identity"
Cards: Arcane Signet, Commander's Sphere
Correct tags:
  mana_production: {"type": "tap", "produces_any": true, "amount": 1}

Pattern: "{1}, {T}: Add one mana of any color"
Cards: Chromatic Lantern (also has static effect)
Correct tags:
  mana_production: {"type": "tap", "produces_any": true, "amount": 1}
  static_effects: [{"effect": "lands_produce_any_color"}]

Pattern: "Lands you control have '{T}: Add one mana of any color'"
Cards: Chromatic Lantern
This is a STATIC EFFECT, not a mana production tag for the lantern itself.

=== CREATURES WITH TRIGGERS ===

Pattern: "Whenever another creature enters the battlefield under your control,
~ deals damage equal to that creature's power to any target"
Cards: Terror of the Peaks
Correct tags:
  static_effects: [{"effect": "damage_on_creature_etb", "damage_source": "entering_creature_power"}]
  power: 5, toughness: 4

Pattern: "Whenever a nontoken Dragon enters the battlefield under your control,
create a 5/5 red Dragon creature token with flying"
Cards: Lathliss, Dragon Queen
Correct tags:
  static_effects: [{"effect": "draw_on_creature_etb", "condition": "nontoken_dragon"}]
  on_etb: []
  — Actually, the token creation is the trigger:
  static_effects: [{"effect": "token_on_dragon_etb", "token": {"type": "Creature", "power": 5, "toughness": 5}}]

Pattern: "Whenever one or more Dragons you control attack, create that many
6/6 red Dragon creature tokens with flying that are tapped and attacking"
Cards: Utvara Hellkite
Correct tags:
  on_attack: [{"action": "create_token", "count": 1, "token": {"type": "Creature", "power": 6, "toughness": 6}}]
  NOTE: count should match number of attacking dragons, but simplified to 1 for simulation

Pattern: "Whenever ~ deals combat damage to a player, create X Treasure tokens
where X is the damage dealt"
Cards: Old Gnawbone
Correct tags:
  on_attack: [{"action": "create_token", "count": 7, "token": {"type": "Treasure"}}]
  NOTE: Simplified — assumes 7 damage from a 7/7

Pattern: "Eminence — As long as ~ is in the command zone or on the battlefield,
other Dragon spells you cast cost {1} less to cast"
Cards: The Ur-Dragon
Correct tags:
  static_effects: [{"effect": "cost_reduction", "applies_to": "dragon", "amount": 1}]
  NOTE: Eminence works from the command zone — this should ALWAYS be active in simulation

=== DRAW SPELLS ===

Pattern: "Draw three cards, then put two cards from your hand on top of your library
in any order"
Cards: Brainstorm
Correct tags:
  on_resolve: [
    {"action": "draw", "count": 3},
    {"action": "put_back", "count": 2, "destination": "top_of_library"}
  ]

Pattern: "Draw cards equal to the greatest power among creatures you control"
Cards: Rishkar's Expertise, Return of the Wildspeaker (mode 1)
Correct tags:
  on_resolve: [{"action": "draw", "count": 5}]
  NOTE: Simplified — assumes average creature power of 5 for dragon decks

Pattern: "Whenever a creature with power 3 or greater enters the battlefield
under your control, draw a card"
Cards: Elemental Bond, Garruk's Uprising, Temur Ascendancy
Correct tags:
  static_effects: [{"effect": "draw_on_creature_etb", "condition": "power_3_or_greater"}]

=== BOARD WIPES ===

Pattern: "Choose one — Destroy all Dragon creatures; or Destroy all non-Dragon creatures"
Cards: Crux of Fate
Correct tags:
  on_resolve: [{"action": "destroy", "target": "all_non_type"}]
  NOTE: Simulation should choose "destroy non-Dragons" for a dragon deck

Pattern: "Destroy all creatures that aren't of the chosen type"
Cards: Kindred Dominance
Correct tags:
  on_resolve: [{"action": "destroy", "target": "all_non_type"}]
"""