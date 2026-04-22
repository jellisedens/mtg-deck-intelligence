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
Cards: Nature's Lore, Skyshroud Claim (searches for TWO Forest cards)
Correct tags (Nature's Lore):
  on_resolve: [
    {"action": "search_land", "count": 1, "destination": "battlefield", "enters_tapped": false, "land_type": "forest"},
    {"action": "shuffle_library"}
  ]
Correct tags (Skyshroud Claim):
  on_resolve: [
    {"action": "search_land", "count": 2, "destination": "battlefield", "enters_tapped": false, "land_type": "forest"},
    {"action": "shuffle_library"}
  ]
NOTE: Nature's Lore and Skyshroud Claim put lands onto the battlefield UNTAPPED.

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
Cards: Rampant Growth, Sakura-Tribe Elder, Pilgrim's Eye
Correct tags:
  on_resolve: [
    {"action": "search_land", "count": 1, "destination": "battlefield", "enters_tapped": true, "land_type": "basic"},
    {"action": "shuffle_library"}
  ]

Pattern: "Search your library for a land card, put it onto the battlefield tapped"
Cards: Tempt with Discovery, Hour of Promise, Pir's Whim
Correct tags:
  on_resolve: [
    {"action": "search_land", "count": 1, "destination": "battlefield", "enters_tapped": true, "land_type": "any"},
    {"action": "shuffle_library"}
  ]

Pattern: "Search your library for a basic land card, put it into your hand"
Cards: Lay of the Land, Traveler's Amulet
Correct tags:
  on_resolve: [
    {"action": "search_land", "count": 1, "destination": "hand", "land_type": "basic"},
    {"action": "shuffle_library"}
  ]

=== FETCH LANDS ===

Pattern: "Pay 1 life, sacrifice ~: Search your library for a [type A] or [type B]
card, put it onto the battlefield, then shuffle"
Cards: Flooded Strand, Polluted Delta, Windswept Heath, Wooded Foothills,
       Bloodstained Mire, Marsh Flats, Scalding Tarn, Verdant Catacombs,
       Arid Mesa, Misty Rainforest
Correct tags:
  is_land: true
  permanent: true
  enters_tapped: false
  mana_production: null (fetch lands don't tap for mana — they sacrifice)
  on_etb: []
  static_effects: []
NOTE: For simulation, treat fetch lands as: when played, immediately sacrifice and
search for a land. Use this simplified representation:
  on_etb: [
    {"action": "search_land", "count": 1, "destination": "battlefield", "enters_tapped": false, "land_type": "any"},
    {"action": "shuffle_library"}
  ]
The fetch land itself leaves the battlefield after use. For simulation purposes,
the searched land replaces it.

Pattern: "{T}, sacrifice ~: Search your library for a basic land card, put it
onto the battlefield tapped"
Cards: Evolving Wilds, Terramorphic Expanse, Fabled Passage
Correct tags:
  is_land: true
  permanent: true
  enters_tapped: false
  mana_production: null
  on_etb: [
    {"action": "search_land", "count": 1, "destination": "battlefield", "enters_tapped": true, "land_type": "basic"},
    {"action": "shuffle_library"}
  ]
NOTE: Fabled Passage enters untapped if you control 4+ lands. For simulation,
treat as tapped (conservative estimate).

=== LANDS ===

Pattern: "enters the battlefield tapped unless you pay 2 life"
Cards: Stomping Ground, Breeding Pool, Blood Crypt, Temple Garden, Hallowed Fountain,
       Godless Shrine, Sacred Foundry, Steam Vents, Overgrown Tomb, Watery Grave
Correct tags:
  enters_tapped: false (ALWAYS assume pay 2 life in simulation — aggressive play)
  mana_production: {"type": "tap", "produces_choice": ["R", "G"], "produces_any": false, "amount": 1}
COMMON MISTAKE: Do NOT set enters_tapped: true for shock lands.
COMMON MISTAKE: Do NOT use produces: {"R": 1, "G": 1} — use produces_choice since you pick ONE.

Pattern: "enters the battlefield tapped unless you control two or more basic lands"
Cards: Cinder Glade, Canopy Vista, Prairie Stream, Sunken Hollow, Smoldering Marsh
Correct tags:
  enters_tapped: true (conservative — early game you often don't have 2 basics)
  mana_production: {"type": "tap", "produces_choice": ["R", "G"], "produces_any": false, "amount": 1}

Pattern: "~ enters the battlefield tapped"
Cards: Temple of Abandon, Dimir Guildgate, Thornwood Falls, Bojuka Bog
Correct tags:
  enters_tapped: true

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

Pattern: "~ enters the battlefield tapped. When ~ enters, scry 1."
Cards: Temple of Abandon, Temple of Deceit, Temple of Enlightenment
Correct tags:
  enters_tapped: true
  on_etb: [{"action": "scry", "count": 1}]

=== MANA DORKS ===

Pattern: "{T}: Add {G}" (or any single color)
Cards: Llanowar Elves, Elvish Mystic, Fyndhorn Elves, Avacyn's Pilgrim
Correct tags:
  permanent: true
  mana_production: {"type": "tap", "produces": {"G": 1}, "amount": 1}
  power: 1, toughness: 1

Pattern: "{T}: Add one mana of any color"
Cards: Birds of Paradise, Noble Hierarch, Sylvan Caryatid
Correct tags:
  permanent: true
  mana_production: {"type": "tap", "produces_any": true, "amount": 1}
NOTE: Birds of Paradise has power 0, toughness 1 — it cannot deal combat damage.

Pattern: "{T}: Add {G}{G}" or "{T}: Add {C}{C}"
Cards: Priest of Titania (adds G per elf), Palladium Myr
Correct tags:
  permanent: true
  mana_production: {"type": "tap", "produces": {"G": 2}, "amount": 2}

=== MANA ROCKS ===

Pattern: "{T}: Add {C}{C}"
Cards: Sol Ring, Mind Stone (also has draw ability)
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

Pattern: "{T}: Add {C}" with additional draw ability
Cards: Mind Stone ("{1}, {T}, Sacrifice: Draw a card")
Correct tags:
  mana_production: {"type": "tap", "produces": {"C": 1}, "amount": 1}
NOTE: The sacrifice-for-draw is an activated ability, not captured in basic sim tags.

Pattern: "{1}, {T}: Add one mana of any of ~ chosen colors"
Cards: Fellwar Stone, Coldsteel Heart
Correct tags:
  mana_production: {"type": "tap", "produces_any": true, "amount": 1}
NOTE: Fellwar Stone's output depends on opponents — treat as any-color for simulation.

=== SIGNETS AND TALISMANS ===

Pattern: "{1}, {T}: Add {W}{U}" (or any two-color combination)
Cards: Azorius Signet, Simic Signet, Gruul Signet, Orzhov Signet, etc.
Correct tags:
  mana_production: {"type": "tap", "produces": {"W": 1, "U": 1}, "amount": 2}
NOTE: Signets require {1} to activate but produce 2 mana. For simulation,
treat as net +1 mana. The produces field shows BOTH colors because you get both.

Pattern: "{T}: Add {C}. {T}: Add {G} or {U}. ~ deals 1 damage to you."
Cards: Talisman of Curiosity, Talisman of Creativity, Talisman of Dominance, etc.
Correct tags:
  mana_production: {"type": "tap", "produces_choice": ["G", "U"], "produces_any": false, "amount": 1}
NOTE: Talismans can tap for colorless OR one of two colors. Simplified to the colored option.

=== BOUNCE LANDS ===

Pattern: "~ enters the battlefield tapped. When ~ enters, return a land you control
to its owner's hand. {T}: Add {G}{U}."
Cards: Simic Growth Chamber, Boros Garrison, Golgari Rot Farm, etc.
Correct tags:
  enters_tapped: true
  mana_production: {"type": "tap", "produces": {"G": 1, "U": 1}, "amount": 2}
  on_etb: [{"action": "return_to_hand", "target": "land"}]
NOTE: Bounce lands produce 2 mana but bounce a land. Net effect is +1 mana next turn.

=== CREATURES WITH TRIGGERS ===

Pattern: "Whenever another creature enters the battlefield under your control,
~ deals damage equal to that creature's power to any target"
Cards: Terror of the Peaks, Warstorm Surge
Correct tags:
  static_effects: [{"effect": "damage_on_creature_etb", "damage_source": "entering_creature_power"}]
  power: 5, toughness: 4

Pattern: "Whenever a nontoken Dragon enters the battlefield under your control,
create a 5/5 red Dragon creature token with flying"
Cards: Lathliss, Dragon Queen
Correct tags:
  static_effects: [{"effect": "token_on_dragon_etb", "token": {"type": "Creature", "power": 5, "toughness": 5}}]

Pattern: "Whenever one or more Dragons you control attack, create that many
6/6 red Dragon creature tokens with flying that are tapped and attacking"
Cards: Utvara Hellkite
Correct tags:
  on_attack: [{"action": "create_token", "count": 1, "token": {"type": "Creature", "power": 6, "toughness": 6}}]
  NOTE: count should match number of attacking dragons, but simplified to 1

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

Pattern: "Whenever you cast a creature spell, draw a card"
Cards: Beast Whisperer, Guardian Project (nontoken, different name)
Correct tags:
  static_effects: [{"effect": "draw_on_creature_etb", "condition": "any"}]
NOTE: Technically triggers on cast not ETB, but for simulation purposes treat as ETB.

=== EQUIPMENT ===

Pattern: "Equipped creature has hexproof and haste. Equip {1}"
Cards: Swiftfoot Boots
Correct tags:
  permanent: true
  static_effects: [{"effect": "haste", "applies_to": "equipped"}]
NOTE: For simulation, haste on equipment means one creature can attack immediately.
Simplified — doesn't track which creature is equipped.

Pattern: "Equipped creature has shroud. Equip {0}"
Cards: Lightning Greaves
Correct tags:
  permanent: true
  static_effects: [{"effect": "haste", "applies_to": "equipped"}]

Pattern: "Equipped creature gets +X/+Y"
Cards: Sword of Feast and Famine, various equipment
Correct tags:
  permanent: true
  static_effects: [{"effect": "anthem", "applies_to": "equipped", "power_bonus": X, "toughness_bonus": Y}]

=== COUNTERSPELLS AND INTERACTION ===

Pattern: "Counter target spell"
Cards: Counterspell, Negate, Swan Song, Dovin's Veto, Mana Drain
Correct tags:
  permanent: false
  on_resolve: []
  static_effects: []
NOTE: In goldfish simulation (no opponent), counterspells do NOTHING. Tag them with
empty on_resolve. The simulator will hold them in hand as uncastable/dead cards,
which accurately reflects that they don't advance your board in solitaire.
This is INTENTIONAL — counterspells being dead cards in goldfish simulation
shows the tradeoff of running interaction.

=== TUTORS ===

Pattern: "Search your library for a card and put that card into your hand"
Cards: Demonic Tutor, Vampiric Tutor (top of library), Worldly Tutor (creature, top)
Correct tags (Demonic Tutor):
  on_resolve: [{"action": "draw", "count": 1}]
NOTE: Simplified — tutors effectively draw the best card. For simulation,
treat as drawing 1 card since we can't model the selection.

Pattern: "Search your library for a creature card and put it into your hand"
Cards: Eladamri's Call, Worldly Tutor, Finale of Devastation
Correct tags:
  on_resolve: [{"action": "draw", "count": 1}]

Pattern: "Search your library for up to five Dragon cards" (Tiamat)
Correct tags:
  on_resolve: [{"action": "draw", "count": 5}]
  on_etb: [{"action": "draw", "count": 5}]
NOTE: Tiamat is an ETB trigger, not a cast trigger. Use on_etb.

=== DRAW SPELLS ===

Pattern: "Draw three cards, then put two cards from your hand on top of your library"
Cards: Brainstorm
Correct tags:
  on_resolve: [
    {"action": "draw", "count": 3},
    {"action": "put_back", "count": 2, "destination": "top_of_library"}
  ]

Pattern: "Draw cards equal to the greatest power among creatures you control"
Cards: Rishkar's Expertise, Return of the Wildspeaker (mode 1), Soul's Majesty
Correct tags:
  on_resolve: [{"action": "draw", "count": 5}]
  NOTE: Simplified — assumes average creature power of 5 for dragon decks

Pattern: "Whenever a creature with power 3 or greater enters the battlefield
under your control, draw a card"
Cards: Elemental Bond, Garruk's Uprising, Temur Ascendancy
Correct tags:
  static_effects: [{"effect": "draw_on_creature_etb", "condition": "power_3_or_greater"}]

Pattern: "Whenever a creature with power 4 or greater enters the battlefield
under your control, draw a card"
Cards: Kiora, Behemoth Beckoner, Colossal Majesty
Correct tags:
  static_effects: [{"effect": "draw_on_creature_etb", "condition": "power_4_or_greater"}]

Pattern: "At the beginning of your upkeep, you may draw X additional cards.
For each card drawn this way, pay X life or put it back"
Cards: Sylvan Library
Correct tags:
  static_effects: [{"effect": "draw_on_creature_etb", "condition": "any"}]
NOTE: Simplified — Sylvan Library is complex. For simulation, treat as
drawing 1 extra card per turn (conservative, assumes paying life for 1).

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

Pattern: "Destroy all creatures"
Cards: Wrath of God, Damnation, Day of Judgment, Blasphemous Act
Correct tags:
  on_resolve: [{"action": "destroy", "target": "all_creatures"}]

Pattern: "Destroy all nonland permanents"
Cards: Austere Command, Merciless Eviction (exile version)
Correct tags:
  on_resolve: [{"action": "destroy", "target": "all_nonland"}]

=== EXTRA COMBAT ===

Pattern: "Whenever ~ attacks, if it's the first combat phase of the turn,
untap all attacking creatures. After this phase, there is an additional combat phase."
Cards: Scourge of the Throne
Correct tags:
  on_attack: [{"action": "extra_combat"}]
NOTE: Extra combat means creatures can attack again. For simulation power tracking,
this effectively doubles the damage output for that turn.

Pattern: "At the beginning of combat on your turn, you may pay {5}{R}{R}.
If you do, untap all creatures you control, and after this phase,
there is an additional combat phase."
Cards: Hellkite Charger
Correct tags:
  on_attack: [{"action": "extra_combat"}]
NOTE: Requires mana payment. For simulation, treat as conditional extra combat.

=== REANIMATION ===

Pattern: "Return target creature card from your graveyard to the battlefield"
Cards: Reanimate, Animate Dead, Necromancy
Correct tags:
  on_resolve: []
NOTE: In goldfish simulation, reanimation depends on having creatures in the graveyard.
For simplicity, treat as empty on_resolve since we don't track graveyard contents
for re-deployment in basic simulation.

=== SACRIFICE OUTLETS ===

Pattern: "Sacrifice a creature: Add {C}{C}"
Cards: Ashnod's Altar
Correct tags:
  permanent: true
  mana_production: null
NOTE: Sacrifice outlets are conditional mana sources. For simulation,
don't treat as reliable mana production since it requires sacrificing creatures.

Pattern: "Sacrifice a creature: Scry 1"
Cards: Viscera Seer
Correct tags:
  permanent: true
  power: 1, toughness: 1
NOTE: Sacrifice for scry is a quality-of-life effect, not primary function in goldfish.

=== PLANESWALKERS ===

Pattern: Planeswalker with + loyalty ability that draws cards
Cards: Sarkhan, Fireblood ("+1: Discard a card, draw a card"), Jace, the Mind Sculptor
Correct tags:
  permanent: true
  static_effects: []
NOTE: Planeswalker abilities are complex. For simulation, capture the most commonly
used ability as a simplified effect. For Sarkhan Fireblood:
  mana_production: {"type": "tap", "produces_choice": ["R", "G"], "produces_any": false, "amount": 1}
  (His -2 adds 2 mana for dragon spells — simplified to mana production)
"""