# MTG Deck Intelligence
## Part 2 — Scryfall API Reference

This document will be populated with detailed Scryfall API documentation during the first development session. Key areas to cover:

---

## Endpoints to Use

### Card Search
- GET /cards/search?q={query}
- Returns paginated list of cards matching Scryfall search syntax
- Supports full Scryfall syntax (colors, types, CMC, oracle text, etc.)

### Card by Name
- GET /cards/named?exact={name}
- Returns a single card by exact name
- Also supports fuzzy matching: GET /cards/named?fuzzy={name}

### Card by ID
- GET /cards/{id}
- Returns a card by its Scryfall UUID

### Autocomplete
- GET /cards/autocomplete?q={query}
- Returns up to 20 card name suggestions for autocomplete

### Sets
- GET /sets
- Returns all MTG sets
- GET /sets/{code} — returns a specific set

### Rulings
- GET /cards/{id}/rulings
- Returns rulings for a specific card

---

## Rate Limiting

- Maximum 10 requests per second
- 50-100ms delay between requests recommended
- No API key required
- Be respectful — Scryfall is a free community resource

---

## Search Syntax (Key Operators)

Colors:
- c:red — cards that are red
- c:UR — cards that are blue and red
- c<=RG — cards that are at most red and green

Mana Cost:
- cmc:3 — converted mana cost exactly 3
- cmc>=5 — CMC 5 or more

Types:
- type:creature — creature cards
- type:instant — instant cards
- t:legendary — legendary cards

Oracle Text:
- o:draw — oracle text contains "draw"
- o:"deal damage" — exact phrase

Format Legality:
- f:standard — legal in Standard
- f:modern — legal in Modern
- f:commander — legal in Commander

Rarity:
- r:mythic — mythic rare
- r:rare — rare

Price:
- usd<1 — cards under $1
- usd>=10 — cards $10 or more

---

## Card Object (Key Fields)

```json
{
  "id": "scryfall-uuid",
  "name": "Lightning Bolt",
  "mana_cost": "{R}",
  "cmc": 1.0,
  "type_line": "Instant",
  "oracle_text": "Lightning Bolt deals 3 damage to any target.",
  "colors": ["R"],
  "color_identity": ["R"],
  "legalities": {
    "standard": "not_legal",
    "modern": "legal",
    "commander": "legal"
  },
  "rarity": "uncommon",
  "set": "leb",
  "set_name": "Limited Edition Beta",
  "prices": {
    "usd": "1.50",
    "usd_foil": "25.00"
  },
  "image_uris": {
    "small": "https://...",
    "normal": "https://...",
    "large": "https://..."
  },
  "power": null,
  "toughness": null
}
```

---

## Notes

- Card images are hosted by Scryfall — use image_uris directly, do not cache images
- Price data updates daily
- Card legality updates when ban announcements are made
- Full documentation: https://scryfall.com/docs/api