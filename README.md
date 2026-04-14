# MTG Deck Intelligence

AI-powered Magic: The Gathering deck building, analytics, and simulation.

## Quick Start

```bash
# 1. Clone the repo
git clone <your-repo-url>
cd mtg-deck-intelligence

# 2. Create your .env file (copy from .env.example or set values)
#    Make sure DATABASE_URL, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB are set

# 3. Start everything
docker compose up --build

# 4. Verify it works
#    Open http://localhost:8000/health in your browser
#    You should see: {"status": "ok", "database": "connected", ...}
```

## Services

| Service | URL | Description |
|---------|-----|-------------|
| Backend API | http://localhost:8000 | FastAPI application |
| API Docs | http://localhost:8000/docs | Interactive Swagger UI |
| PostgreSQL | localhost:5432 | Database (internal) |

## Tech Stack

- **Backend:** Python, FastAPI, SQLAlchemy, Alembic
- **Database:** PostgreSQL 16
- **AI:** OpenAI API
- **Card Data:** Scryfall API
- **Infrastructure:** Docker Compose