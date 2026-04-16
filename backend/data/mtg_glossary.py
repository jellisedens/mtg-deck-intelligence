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
  - Cost reduction: o:"cost" o:"less"

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