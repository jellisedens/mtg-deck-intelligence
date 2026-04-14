# MTG Deck Intelligence
## Part 3 — Implementation Plan

This document defines the sequential build process for the project.

---

## Development Phases

### Phase 1 — Environment Setup

Goal:
Create a local development environment.

Tasks:
- Create repository
- Setup Docker
- Setup PostgreSQL container
- Setup FastAPI backend scaffold

Output:
Running backend + database.

Directory structure:

backend/
  api/
  models/
  services/
  simulation/
  database/
  main.py

---

### Phase 2 — Database Schema

Goal:
Implement database tables.

Tables:

users
decks
deck_cards
simulation_results

Fields:

users — id (UUID), email, password_hash, created_at

decks — id (UUID), user_id (FK), name, format, description, created_at, updated_at

deck_cards — id (UUID), deck_id (FK), scryfall_id, card_name, quantity, board (main/sideboard/commander)

simulation_results — id (UUID), deck_id (FK), simulation_type, results_json, created_at

Tasks:
- Create SQLAlchemy models
- Setup Alembic migrations
- Create initial migration

Note: Card data is fetched from Scryfall at runtime — not stored locally. Only the scryfall_id and card_name are stored in deck_cards for reference.

---

### Phase 3 — Scryfall API Integration

Goal:
Build a service layer for interacting with the Scryfall API.

Endpoints to integrate:
- Card search (with full syntax support)
- Card by name (exact + fuzzy)
- Card autocomplete
- Set listing

Features:
- Rate limiting (respect 10 req/sec)
- Response caching (cache card data for 1 hour to reduce API calls)
- Error handling for network failures

Service location: backend/services/scryfall.py

---

### Phase 4 — Deck CRUD + Authentication

Goal:
Allow users to create accounts and manage decks.

Endpoints:

POST /auth/signup
POST /auth/login

POST /decks — create a deck
GET /decks — list user's decks
GET /decks/{id} — get deck with cards
PUT /decks/{id} — update deck name/description
DELETE /decks/{id} — delete a deck

POST /decks/{id}/cards — add card to deck
DELETE /decks/{id}/cards/{card_id} — remove card
PUT /decks/{id}/cards/{card_id} — update quantity

Features:
- JWT authentication (same pattern as RAG project)
- Deck validation (format-legal card count, singleton rules for Commander)

---

### Phase 5 — Deck Analytics

Goal:
Calculate and return deck statistics.

Endpoint:

GET /decks/{id}/analytics

Analytics to compute:
- Mana curve (count of cards at each CMC 0-7+)
- Color distribution (count of mana symbols by color)
- Card type distribution (creatures, instants, sorceries, etc.)
- Mana base analysis (land count, color sources, fixing)
- Average CMC
- Deck composition summary

Process:
1. Fetch all cards in deck
2. For each card, fetch full data from Scryfall (cached)
3. Compute statistics
4. Return structured JSON for frontend visualization

---

### Phase 6 — AI Card Suggestions

Goal:
Use AI to suggest cards for a deck.

Endpoint:

POST /decks/{id}/suggest

Process:
1. Fetch current deck composition
2. Fetch card details from Scryfall
3. Build a prompt with deck context (format, colors, strategy, current cards, mana curve)
4. Send to OpenAI API
5. AI suggests cards with reasoning
6. For each suggestion, verify it exists via Scryfall
7. Return suggestions with card images and explanation

AI context should include:
- Current deck list with quantities
- Mana curve analysis
- Missing card types or roles
- Format legality constraints
- User's stated strategy or theme

---

### Phase 7 — Opening Hand Simulator

Goal:
Simulate drawing opening hands and calculate probabilities.

Endpoint:

POST /decks/{id}/simulate/hand

Features:
- Draw 7 random cards from the deck
- Mulligan simulation (London mulligan)
- Run N simulations (default 1000)
- Calculate probabilities:
  - Chance of having X lands in opening hand
  - Chance of having a 1-drop, 2-drop, etc.
  - Chance of having specific cards or card types

---

### Phase 8 — Game State Simulation

Goal:
Simulate early turns to estimate deck performance.

Endpoint:

POST /decks/{id}/simulate/game

Features:
- Simulate turns 1-7
- Track: lands played, spells cast, creatures on board, mana available
- Calculate per-turn statistics:
  - Probability of playing on curve
  - Total power on board by turn
  - Total damage dealt by turn
- Run N simulations and aggregate results
- Visualize as turn-by-turn performance graph

---

### Phase 9 — Frontend

Goal:
Build the user interface.

Pages:
- Login/Signup
- Deck list (all user decks)
- Deck builder (card search, add/remove, real-time analytics)
- Deck analytics dashboard (charts, statistics)
- Simulation results (hand simulator, game simulator)
- AI suggestions panel

Key Components:
- Card search with autocomplete
- Card display (image, stats)
- Deck list editor (drag/drop or +/- buttons)
- Mana curve chart
- Color pie chart
- Hand simulator with visual card display
- Turn-by-turn performance graph