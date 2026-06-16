from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database.session import get_db
from models.user import User
from models.deck import Deck
from models.deck_card import DeckCard
from api.deps import get_verified_user
from api.schemas.suggest import SuggestRequest, SuggestResponse
from services.ai_suggest import get_suggestions
from services.scryfall import scryfall_service

router = APIRouter(prefix="/ai", tags=["ai suggestions"])


@router.post("/suggest", response_model=SuggestResponse)
async def suggest_cards(
    request: SuggestRequest,
    user: User = Depends(get_verified_user),
    db: Session = Depends(get_db),
):
    """
    AI-powered card suggestions.
    Pre-fetches card data and uses cached strategy profile for fast responses.
    """
    deck_cards = None
    deck_info = None
    simulation_data = None
    card_lookup = None

    

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
            "preferences": deck.preferences,
            "deck_intelligence": deck.deck_intelligence,
        }

        # Use cached simulation from strategy profile
        profile = deck.strategy_profile or {}
        simulation_data = profile.get("cached_simulation")

        # Pre-fetch card data from Scryfall (bulk, fast)
        identifiers = [{"id": c.scryfall_id} for c in deck_cards]
        scryfall_data = await scryfall_service.get_collection(identifiers)
        if "data" in scryfall_data:
            card_lookup = {c["id"]: c for c in scryfall_data["data"]}

    result = await get_suggestions(
        prompt=request.prompt,
        deck_cards=deck_cards,
        deck_info=deck_info,
        simulation_data=simulation_data,
        card_lookup=card_lookup,
        conversation_context=request.conversation_context,
        intent_override=request.intent_override,
        is_clarification_response=request.is_clarification_response,
    )

    if "error" in result:
        raise HTTPException(status_code=502, detail=result.get("details", "AI suggestion failed"))

    return result