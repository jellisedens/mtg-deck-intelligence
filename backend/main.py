from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.health import router as health_router
from api.scryfall import router as scryfall_router
from api.auth import router as auth_router
from api.decks import router as decks_router
from api.analytics import router as analytics_router
from api.suggest import router as suggest_router
from api.strategy import router as strategy_router
from api.simulation import router as simulation_router
from api.strategy_stream import router as strategy_stream_router
from api.deck_import import router as deck_import_router

app = FastAPI(
    title="MTG Deck Intelligence",
    description="AI-powered Magic: The Gathering deck building and analytics",
    version="0.1.0",
)

# CORS — allow frontend dev server to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(health_router)
app.include_router(scryfall_router)
app.include_router(auth_router)
app.include_router(decks_router)
app.include_router(analytics_router)
app.include_router(suggest_router)
app.include_router(strategy_router)
app.include_router(simulation_router)
app.include_router(strategy_stream_router)
app.include_router(deck_import_router)

@app.get("/")
def root():
    return {"message": "MTG Deck Intelligence API", "docs": "/docs"}