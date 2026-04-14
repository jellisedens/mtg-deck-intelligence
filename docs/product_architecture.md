# MTG Deck Intelligence
## Part 1 — Product & Architecture

## Product Overview

An AI-powered application that helps Magic: The Gathering players build optimized decks, analyze deck performance through statistical simulation, and get intelligent card suggestions. The app integrates with the Scryfall API for real-time card data and search.

---

## Core Features (Priority Order)

### Phase 1 — Deck Building + AI Suggestions
- Users can create, save, and manage decks
- Search for cards using Scryfall API integration (supports Scryfall's full search syntax)
- AI assistant suggests cards based on deck strategy, mana curve, synergies, and format legality
- Add/remove cards with real-time deck composition updates
- Support for different formats (Standard, Modern, Commander, Pioneer, etc.)

### Phase 2 — Deck Analytics
- Mana curve visualization — distribution of cards by mana cost
- Color distribution — breakdown of mana symbols across the deck
- Card type distribution — creatures, instants, sorceries, enchantments, etc.
- Mana base analysis — ratio of lands to spells, color fixing coverage

### Phase 3 — Statistical Simulation
- Opening hand simulator — draw 7 cards, mulligan decisions, probability of hitting key cards
- Mana/land draw probability — likelihood of hitting land drops on curve through turns 1-7
- Damage output simulation — estimate total damage capability by turn (creature power on board)
- Deck performance tracking — aggregate statistics across multiple simulated games to gauge consistency

### Phase 4 (Later) — Pack/Box Expected Value Calculator
- Estimate value of booster boxes based on set card prices
- Calculate expected mythic/rare/uncommon pull rates
- Compare expected value across different products
- Not building this yet — focus on Phases 1-3 first

---

## External API: Scryfall

- Base URL: https://api.scryfall.com
- Card search: GET /cards/search?q={query} — supports full Scryfall syntax
- Card by name: GET /cards/named?exact={name}
- Random card: GET /cards/random
- Sets: GET /sets
- Rate limit: 50-100ms delay between requests, 10 requests/second max
- No API key required — free public API
- Documentation: https://scryfall.com/docs/api

---

## AI Integration Points

The AI assistant helps with:

1. Card suggestions — "I'm building a red/blue aggro deck in Standard, suggest creatures for my 2-drop slot"
2. Deck critique — "Analyze my deck and tell me what's weak" (looks at curve, synergies, missing pieces)
3. Strategy advice — "How should I build my mana base for a 3-color Commander deck?"
4. Scryfall query building — user says "find me cheap red removal spells" and the AI translates to Scryfall syntax: c:red type:instant o:damage cmc<=2

The AI should have context about:
- Current deck composition
- Format rules and ban lists
- General MTG strategy principles (curve, tempo, card advantage, etc.)

---

## Recommended Technology Stack

Frontend:
- Next.js
- React
- TypeScript
- Tailwind CSS
- Recharts or D3 for visualizations

Backend:
- Python
- FastAPI

Database:
- PostgreSQL

AI Integration:
- OpenAI API (GPT-4o-mini for suggestions and analysis)

External API:
- Scryfall (card data, search, pricing)

Infrastructure:
- Docker

---

## High-Level Architecture

Frontend (Next.js)
↓
Backend API (FastAPI)
↓
Application Services
- Deck Management Service
- Scryfall Integration Service
- AI Suggestion Service
- Simulation Engine

↓
Database Layer
- PostgreSQL

↓
External Services
- OpenAI API
- Scryfall API

---

## Project Structure

mtg-deck-intelligence/
├── backend/
│   ├── api/            # FastAPI route handlers
│   ├── models/         # SQLAlchemy ORM models
│   ├── services/       # Business logic
│   ├── simulation/     # Statistical simulation engine
│   ├── database/       # Database connection and session config
│   └── main.py
├── frontend/
│   ├── app/            # Next.js pages
│   ├── components/     # React components
│   └── lib/            # API helpers, types
├── docker/
├── docs/
├── docker-compose.yml
└── README.md