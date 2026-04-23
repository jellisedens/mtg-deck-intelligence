from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.session import get_db
from models.user import User
from models.deck import Deck
from models.deck_card import DeckCard
from api.deps import get_current_user
from api.schemas.suggest import SuggestRequest, SuggestResponse
from services.ai_suggest import get_suggestions
from services.scryfall import scryfall_service
from simulation.sim_tags import generate_sim_tags
from simulation.game_engine import run_simulation

router = APIRouter(prefix="/ai", tags=["ai suggestions"])

# Sim tag cache (shared with simulation.py)
_sim_tag_cache = {}


async def _get_simulation_data(deck, deck_cards, db) -> dict | None:
    """
    Run a quick simulation to get performance data for AI context.
    Uses cached sim tags if available. Returns None if sim fails.
    """
    try:
        # Fetch Scryfall data
        identifiers = [{"id": card.scryfall_id} for card in deck_cards]
        scryfall_data = await scryfall_service.get_collection(identifiers)
        if "error" in scryfall_data:
            return None

        card_lookup = {c["id"]: c for c in scryfall_data.get("data", [])}

        # Build main deck card list
        main_deck = []
        for dc in deck_cards:
            if dc.board != "main":
                continue
            card_data = card_lookup.get(dc.scryfall_id)
            if card_data:
                main_deck.append({"card_data": card_data, "quantity": dc.quantity})

        if not main_deck:
            return None

        # Get sim tags — prefer strategy profile cache, then memory cache
        sim_tags = None
        profile = deck.strategy_profile or {}
        if profile.get("sim_tags"):
            sim_tags = profile["sim_tags"]
        else:
            cache_key = str(deck.id)
            if cache_key in _sim_tag_cache:
                sim_tags = _sim_tag_cache[cache_key]
            else:
                # No cached tags — skip simulation rather than waiting 3 min
                return None

        # Run a quick 100-game simulation (fast since tags are cached)
        result = run_simulation(
            deck_cards=main_deck,
            sim_tags=sim_tags,
            n_games=100,
            turns=10,
        )
        return result

    except Exception:
        return None


@router.post("/suggest", response_model=SuggestResponse)
async def suggest_cards(
    request: SuggestRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    AI-powered card suggestions.

    Two modes:
    - With deck_id: analyzes your deck and gives targeted advice
      (includes simulation performance data if sim tags are cached)
    - Without deck_id: acts as a smart MTG search assistant
    """
    deck_cards = None
    deck_info = None
    simulation_data = None

    if request.deck_id:
        deck = db.query(Deck).filter(Deck.id == request.deck_id).first()
        if not deck:
            raise HTTPException(status_code=404, detail="Deck not found")
        if deck.user_id != user.id:
            raise HTTPException(status_code=403, detail="Not your deck")

        deck_cards = db.query(DeckCard).filter(DeckCard.deck_id == deck.id).all()
        deck_info = {
            "name": deck.name,
            "format": deck.format,
            "description": deck.description,
            "strategy_profile": deck.strategy_profile,
        }

        # Get simulation data if sim tags are already cached
        simulation_data = await _get_simulation_data(deck, deck_cards, db)

    result = await get_suggestions(
        prompt=request.prompt,
        deck_cards=deck_cards,
        deck_info=deck_info,
        simulation_data=simulation_data,
    )

    if "error" in result:
        raise HTTPException(status_code=502, detail=result.get("details", "AI suggestion failed"))

    return result