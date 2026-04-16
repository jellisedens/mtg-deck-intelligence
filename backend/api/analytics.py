from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.session import get_db
from models.user import User
from models.deck import Deck
from models.deck_card import DeckCard
from api.deps import get_current_user
from api.schemas.analytics import AnalyticsResponse
from services.analytics import compute_analytics

router = APIRouter(prefix="/decks", tags=["analytics"])


@router.get("/{deck_id}/analytics", response_model=AnalyticsResponse)
async def get_deck_analytics(
    deck_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Compute and return analytics for a deck.
    Fetches full card data from Scryfall and calculates:
    - Mana curve
    - Color distribution
    - Card type distribution
    - Mana base analysis
    - Average CMC
    - Deck composition summary
    """
    # Verify deck exists and belongs to user
    deck = db.query(Deck).filter(Deck.id == deck_id).first()
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")
    if deck.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your deck")

    # Get all cards in the deck
    cards = db.query(DeckCard).filter(DeckCard.deck_id == deck.id).all()

    # Compute analytics (async because it calls Scryfall)
    result = await compute_analytics(cards)

    if "error" in result:
        raise HTTPException(status_code=502, detail=result.get("details", "Failed to fetch card data"))

    return result