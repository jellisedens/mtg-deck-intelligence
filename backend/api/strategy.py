from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.session import get_db
from models.user import User
from models.deck import Deck
from models.deck_card import DeckCard
from api.deps import get_current_user
from services.analytics import compute_analytics
from services.role_classifier import classify_deck_roles
from services.strategy_profiler import generate_strategy_profile

router = APIRouter(prefix="/decks", tags=["strategy"])


@router.post("/{deck_id}/strategy", response_model=dict)
async def generate_deck_strategy(
    deck_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generate (or regenerate) a strategic profile for a deck.
    Analyzes the deck's cards, roles, and analytics to create a
    comprehensive strategy document that informs all future AI interactions.
    """
    deck = db.query(Deck).filter(Deck.id == deck_id).first()
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")
    if deck.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your deck")

    cards = db.query(DeckCard).filter(DeckCard.deck_id == deck.id).all()
    if not cards:
        raise HTTPException(status_code=400, detail="Deck has no cards")

    # Compute analytics with card data
    analytics = await compute_analytics(cards, include_card_data=True)
    card_lookup = analytics.pop("_card_lookup", {})

    # Classify roles
    deck_info = {
        "name": deck.name,
        "format": deck.format,
        "description": deck.description,
    }
    role_data = classify_deck_roles(cards, card_lookup, deck_info)

    # Generate strategy profile
    profile = generate_strategy_profile(
        deck_info=deck_info,
        deck_cards=cards,
        card_lookup=card_lookup,
        analytics=analytics,
        role_data=role_data,
    )

    if "error" in profile:
        raise HTTPException(status_code=502, detail=f"Strategy generation failed: {profile['error']}")

    # Save to database
    deck.strategy_profile = profile
    db.commit()
    db.refresh(deck)

    return profile


@router.get("/{deck_id}/strategy", response_model=dict)
async def get_deck_strategy(
    deck_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get the stored strategic profile for a deck.
    Returns 404 if no profile has been generated yet.
    """
    deck = db.query(Deck).filter(Deck.id == deck_id).first()
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")
    if deck.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your deck")

    if not deck.strategy_profile:
        raise HTTPException(status_code=404, detail="No strategy profile generated yet. Use POST to generate one.")

    return deck.strategy_profile