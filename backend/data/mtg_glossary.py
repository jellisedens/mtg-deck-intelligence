"""
MTG Colloquial Language → Scryfall Translation System

Players use informal strategic terms that don't appear on cards.
This glossary maps those terms to real Scryfall query mechanics.

RULES:
- NEVER search using slang terms directly (e.g., o:ramp, o:removal, o:"card draw")
- ALWAYS map to real mechanics, oracle text, or card types
- Use MULTIPLE focused queries to cover the concept space
- Use id<= for Commander color identity
- Always include f:commander when format is known
- Prefer multiple narrow queries over one broad query
"""

GLOSSARY = """
CRITICAL — MTG COLLOQUIAL LANGUAGE TRANSLATION SYSTEM
Players frequently use informal or strategic terms that DO NOT appear in card text.
You MUST translate these into Scryfall-compatible mechanics and queries.

GENERAL RULE:
- NEVER search using slang terms directly (e.g., o:ramp, o:removal, o:"card draw")
- ALWAYS map to real mechanics, oracle text, or card types
- Use MULTIPLE focused queries to cover the concept space

---
MANA & RESOURCE DEVELOPMENT

"ramp" / "mana acceleration"
  - Mana dorks: t:creature o:"{T}: Add"
  - Mana rocks: t:artifact o:"{T}: Add" cmc<=3
  - Land ramp: (o:"search your library" o:land) OR (o:"put" o:land o:battlefield)
  - Extra land drops: o:"additional land"
  - Cost reducers / medallions: o:"spells you cast cost" o:"less" (e.g., Sapphire Medallion, Ruby Medallion, Jet Medallion, Pearl Medallion, Emerald Medallion, Urza's Incubator, Herald's Horn)
  - Cost reducers by type: o:"cost" o:"{1} less" OR o:"cost" o:"{2} less"
  YOU MUST generate at least one query for EACH of these subcategories when the user asks for "ramp"

"mana fixing" / "color fixing"
  - t:land (o:"any color" OR o:"add one mana of any")
  - t:artifact o:"any color"

"treasure" / "treasure tokens"
  - o:"create" o:"treasure"

---
CARD ADVANTAGE

"card draw" / "draw engine"
  - o:"draw" o:"card"
  - Repeatable: t:creature o:"draw" OR t:enchantment o:"draw"

"card advantage"
  - o:"draw"
  - o:"return" o:"graveyard"
  - o:"exile" o:"play" OR o:"exile" o:"cast"

"wheel" / "wheeling"
  - o:"each player" o:"discard" o:"draw"

"cantrip"
  - o:"draw a card" cmc<=2

"impulse draw"
  - o:"exile the top" o:"you may play"

---
REMOVAL & INTERACTION

"removal"
  - o:"destroy" OR o:"exile"
  - o:"damage" o:"target"

"spot removal" / "targeted removal"
  - o:"destroy target" OR o:"exile target"

"board wipe" / "sweeper" / "wrath"
  - o:"destroy all"
  - o:"all creatures get"
  - o:"exile all"

"interaction"
  - t:instant
  - o:"counter target"
  - o:"exile target"

---
TUTORS & SEARCH

"tutor"
  - o:"search your library"

"fetch" (when referring to cards, not fetch lands)
  - o:"search your library" o:"land"

"fetch lands"
  - t:land o:"search your library" o:"land"

---
STRATEGY ARCHETYPES

"stax"
  - o:"can't"
  - o:"each player" o:"sacrifice"
  - o:"tap" o:"doesn't untap"

"aristocrats" / "sacrifice" / "sac"
  - o:"sacrifice"
  - o:"whenever" o:"dies"

"tokens" / "token generation" / "go wide"
  - o:"create" o:"token"

"spellslinger"
  - o:"whenever you cast" o:"instant"
  - o:"whenever you cast" o:"sorcery"
  - o:"instant or sorcery"

"storm"
  - keyword:storm
  - o:"copy" o:"for each"

"blink" / "flicker"
  - o:"exile" o:"return" o:"battlefield"

"reanimator" / "reanimation" / "graveyard recursion"
  - o:"return" o:"from your graveyard" o:"battlefield"
  - o:"put" o:"graveyard" o:"battlefield"

"landfall"
  - o:"whenever a land enters"
  - o:"land enters the battlefield"

"voltron"
  - t:equipment
  - t:aura o:"enchanted creature"

"tribal" / "typal"
  - Use the creature type directly: t:dragon, t:goblin, t:elf, etc.
  - Tribal support: o:"choose a creature type" OR o:"of the chosen type"

"mill" / "milling"
  - o:"mill" OR o:"put the top" o:"graveyard"

"infect" / "poison"
  - keyword:infect OR o:"poison counter"

"energy"
  - o:"energy counter" OR o:"{E}"

---
COMBAT & WIN CONDITIONS

"finisher" / "win condition" / "closer"
  - pow>=6
  - o:"you win the game"
  - o:"extra turn"

"aggro" / "aggressive"
  - Low CMC creatures: t:creature cmc<=2
  - Efficient beaters: t:creature pow>=3 cmc<=3

"combat tricks"
  - t:instant o:"target creature gets"

"evasion"
  - keyword:flying
  - keyword:trample
  - o:"can't be blocked"
  - keyword:menace
  - keyword:fear
  - keyword:shadow

"goad"
  - o:goad (official keyword)

"buff" / "pump" / "anthem"
  - o:"creatures you control get" OR o:"+1/+1"

---
PROTECTION & DEFENSE

"protection"
  - o:hexproof
  - o:indestructible
  - o:"protection from"

"pillowfort"
  - o:"can't attack you"
  - o:"attacks you" o:"pay"
  - o:"propaganda" (search by name)

"lifegain" / "life gain"
  - o:"gain" o:"life"

"fog" / "fog effects"
  - o:"prevent all combat damage"

---
CONTROL & TEMPO

"control"
  - Counterspells: o:"counter target"
  - Removal + draw combinations

"tempo"
  - Low-cost interaction + bounce
  - o:"return target" cmc<=3

"bounce"
  - o:"return target" o:"owner's hand"

"tax" / "tax effects"
  - o:"pay" o:"more" OR o:"costs" o:"more"

---
UTILITY & ENGINES

"recursion"
  - o:"return" o:"from your graveyard"

"value engine"
  - Repeatable triggers: o:"whenever" or o:"at the beginning"

"engine"
  - t:artifact OR t:enchantment with repeatable effects

"hate" / "hoser"
  - Cards that shut down specific strategies
  - o:"can't" combined with the strategy type

"budget" / "cheap"
  - Use Scryfall price filter: usd<1, usd<=5, usd<10

---
EXAMPLE TRANSLATIONS

User: "cheap ramp for green deck"
  DO NOT: o:ramp
  DO: t:creature o:"{T}: Add" id<=G cmc<=2 f:commander
      t:artifact o:"{T}: Add" cmc<=2 f:commander
      o:"search your library" o:land id<=G cmc<=3 f:commander

User: "best removal in black and white"
  DO NOT: o:removal
  DO: (o:"destroy target" OR o:"exile target") id<=WB f:commander
      o:"destroy all creatures" id<=WB f:commander

User: "card draw for red"
  DO NOT: o:"card draw"
  DO: o:"draw" o:"card" id<=R f:commander
      o:"exile the top" o:"you may play" id<=R f:commander

User: "find me budget mana rocks under $2"
  DO NOT: o:ramp t:artifact
  DO: t:artifact o:"{T}: Add" cmc<=3 usd<2 f:commander
"""

CLARIFICATIONS = {
    "ramp": {
        "display": "What type of ramp are you looking for?",
        "options": [
            {"label": "Mana dorks", "description": "Creatures that tap for mana (e.g., Llanowar Elves, Birds of Paradise)"},
            {"label": "Mana rocks", "description": "Artifacts that produce mana (e.g., Sol Ring, Arcane Signet)"},
            {"label": "Land ramp", "description": "Spells that search for lands (e.g., Cultivate, Kodama's Reach)"},
            {"label": "Cost reducers", "description": "Cards that make spells cheaper (e.g., Sapphire Medallion, Urza's Incubator)"},
            {"label": "Extra land drops", "description": "Cards that let you play additional lands (e.g., Azusa, Exploration)"},
            {"label": "Treasure/temporary mana", "description": "Cards that create treasure tokens or one-time mana bursts"},
            {"label": "All types", "description": "Show me a mix of everything"},
        ],
    },
    "removal": {
        "display": "What kind of removal do you need?",
        "options": [
            {"label": "Spot removal", "description": "Targeted destroy/exile effects (e.g., Swords to Plowshares, Path to Exile)"},
            {"label": "Board wipes", "description": "Mass removal that clears the board (e.g., Wrath of God, Cyclonic Rift)"},
            {"label": "Artifact/enchantment removal", "description": "Destroy or exile artifacts and enchantments"},
            {"label": "Creature removal", "description": "Cards that specifically deal with creatures"},
            {"label": "Flexible removal", "description": "Cards that can hit multiple permanent types"},
            {"label": "All types", "description": "Show me a mix of everything"},
        ],
    },
    "card draw": {
        "display": "What kind of card draw are you looking for?",
        "options": [
            {"label": "One-shot draw", "description": "Spells that draw cards immediately (e.g., Harmonize, Blue Sun's Zenith)"},
            {"label": "Draw engines", "description": "Permanents that draw repeatedly (e.g., Rhystic Study, Phyrexian Arena)"},
            {"label": "Cantrips", "description": "Cheap spells that replace themselves"},
            {"label": "Impulse draw", "description": "Exile top cards and play them (red-style draw)"},
            {"label": "Wheels", "description": "Everyone discards and draws new hands"},
            {"label": "All types", "description": "Show me a mix of everything"},
        ],
    },
    "interaction": {
        "display": "What kind of interaction are you looking for?",
        "options": [
            {"label": "Counterspells", "description": "Negate or counter opponent's spells"},
            {"label": "Protection", "description": "Hexproof, indestructible, shroud for your permanents"},
            {"label": "Bounce", "description": "Return permanents to hand"},
            {"label": "Tax effects", "description": "Make opponents pay more for spells"},
            {"label": "All types", "description": "Show me a mix of everything"},
        ],
    },
    "lands": {
        "display": "What kind of lands are you looking for?",
        "options": [
            {"label": "Dual lands", "description": "Lands that produce two or more colors"},
            {"label": "Fetch lands", "description": "Lands that search for other lands"},
            {"label": "Utility lands", "description": "Lands with special abilities beyond mana"},
            {"label": "Budget mana fixing", "description": "Affordable lands that fix colors"},
            {"label": "All types", "description": "Show me a mix of everything"},
        ],
    },
    "protection": {
        "display": "What kind of protection do you need?",
        "options": [
            {"label": "Board protection", "description": "Protect all your permanents (e.g., Teferi's Protection)"},
            {"label": "Single target", "description": "Protect one key creature or permanent"},
            {"label": "Graveyard protection", "description": "Prevent exile or protect your graveyard"},
            {"label": "Pillowfort", "description": "Discourage opponents from attacking you"},
            {"label": "All types", "description": "Show me a mix of everything"},
        ],
    },
}

REPLACEMENT_GUIDE = """
CARD REPLACEMENT LOGIC:
When a user asks to replace a specific card, DO NOT search for cards with identical mechanics.
Instead, identify the STRATEGIC ROLE the card fills, then search for alternatives that fill the same role.

Process:
1. Identify what the card DOES for the deck (its strategic role)
2. Search for cards that fill that same role, even with different mechanics
3. Consider budget constraints if mentioned

Example strategic roles:
- Smothering Tithe → "passive MANA generation engine" → search for:
  - o:"create" o:"treasure" t:enchantment f:commander (treasure generators)
  - o:"whenever" o:"add" t:enchantment f:commander (mana triggers)
  - o:"opponent" o:"pay" f:commander (tax effects that generate resources)
  - o:"create" o:"treasure" f:commander (broader treasure generation)
  - Do NOT suggest card DRAW replacements — Smothering Tithe generates MANA, not cards

VALUE TYPE DISTINCTIONS — critical for replacements:
  - MANA generation: cards that produce mana, treasure, or reduce costs
  - CARD DRAW: cards that draw cards or provide card selection
  - BOARD CONTROL: cards that remove or neutralize threats
  - BOARD PRESENCE: cards that create tokens or buff creatures
  - LIFE/DEFENSE: cards that gain life or prevent damage
  Always identify the SPECIFIC value type before searching for replacements.

- Cyclonic Rift → "asymmetric board reset" → search for:
  - o:"each opponent" o:"return" f:commander
  - o:"destroy all" f:commander
  - o:"exile all" f:commander

- Sol Ring → "explosive early ramp" → search for:
  - t:artifact o:"{T}: Add" cmc<=2 f:commander
  - t:artifact o:"add" o:"mana" cmc=0 f:commander

NEVER search for the exact card text of what you're replacing.
ALWAYS think about the ROLE and search for that role broadly.
Generate 3-5 diverse queries covering different angles of the same strategic role.
"""

SYNERGY_RULES = """
SYNERGY-AWARE EVALUATION:
When analyzing a deck or suggesting cuts, you MUST evaluate cards in the context of deck synergy.

TRIBAL SYNERGY:
- If the deck has a primary creature type (dragon, goblin, elf, etc.), cards that reference
  that type by name, grant bonuses to that type, or trigger off that type are HIGH SYNERGY
  and should NEVER be suggested as cuts
- Examples: Dragon Tempest in a dragon deck, Goblin Chieftain in a goblin deck
- Cards that reduce costs for the primary type (Urza's Incubator, Herald's Horn) are CORE INFRASTRUCTURE
- Cards that reference the commander by name or directly enable the commander's strategy are PROTECTED

COMMANDER SYNERGY:
- Cards that directly enable the commander's abilities or strategy are CORE and should never be cut
- Cards referenced in the deck's strategic description as part of a win condition are PROTECTED
- Cards that share mechanical themes with the commander are HIGH SYNERGY

ABILITY TEXT SYNERGY:
- Cards whose ability text directly interacts with the commander's abilities or the deck's
  primary creature type should be weighted heavily
- Example: Savage Ventmaw in a dragon deck that needs mana = HIGH SYNERGY (dragon + mana generation)
- Example: Temur Ascendancy in a deck with many power 4+ creatures = HIGH SYNERGY (draw engine)

CUT PRIORITIES (what to suggest cutting FIRST):
1. Generic goodstuff with no specific synergy to the deck's strategy
2. High CMC cards that don't advance the win condition
3. Redundant effects (if you have 8 removal spells, cutting 1 is fine)
4. Cards that don't match the deck's speed/tempo
5. Cards with anti-synergy (works against the commander or key pieces)
6. Weakest card in an over-represented category

NEVER SUGGEST CUTTING:
- Cards that reference the commander or primary creature type by name or type
- Cards identified as part of a win condition or combo
- Cards that are part of a synergy loop (e.g., Savage Ventmaw + Aggravated Assault)
- Core mana infrastructure (Sol Ring, Arcane Signet, Command Tower)
- Cards with tribal payoffs in a tribal deck
"""

STRATEGIC_CONTEXT = """
STRATEGIC DECK ANALYSIS:
Before making any recommendations, analyze the deck's strategic identity:

1. COMMANDER ROLE: What does the commander do? What strategy does it enable?
   - Read the commander's abilities and determine the optimal game plan
   - The Ur-Dragon: eminence reduces dragon costs, attack trigger draws and cheats permanents into play
     → Strategy: ramp into dragons, attack to generate value, overwhelm with large flyers

2. WIN CONDITIONS: How does this deck actually win?
   - Combat damage (go wide with tokens, go tall with big creatures, commander damage)
   - Combo (infinite loops, instant wins)
   - Value/attrition (outgrind opponents with card advantage)
   - Alternative wins (mill, poison, Thassa's Oracle, Revel in Riches)

3. KEY SYNERGIES: What card interactions are central to the deck?
   - Tribal triggers (Dragon Tempest + dragons entering = damage + haste)
   - Mana loops (Savage Ventmaw + extra combats)
   - Value engines (Temur Ascendancy + big creatures = card draw)

4. STRATEGIC DESCRIPTION: If the deck has a description, treat it as the player's stated intent
   and align all recommendations with that intent

When the deck description is vague or missing, INFER the strategy from:
- The commander's abilities (this is the MOST important signal)
- Creature type concentration (many dragons = dragon tribal synergy matters)
- Card type distribution (heavy creatures = combat, heavy instants = control)
- Mana curve shape (low = aggro, high = ramp into bombs)

ALWAYS state your understanding of the deck's strategy in your summary.
This shows the user you understand their deck and builds trust in your suggestions.
"""