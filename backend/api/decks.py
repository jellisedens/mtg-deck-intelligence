from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database.session import get_db
from models.user import User
from models.deck import Deck
from models.deck_card import DeckCard
from api.deps import get_current_user
from api.schemas.deck import (
    DeckCreate,
    DeckUpdate,
    DeckResponse,
    DeckDetailResponse,
    CardAdd,
    CardUpdate,
    DeckCardResponse,
)

router = APIRouter(prefix="/decks", tags=["decks"])


# ─── Helper ────────────────────────────────────────────

def _get_user_deck(deck_id: UUID, user: User, db: Session) -> Deck:
    """Fetch a deck and verify it belongs to the current user."""
    deck = db.query(Deck).filter(Deck.id == deck_id).first()

    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")
    if deck.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your deck")

    return deck


# ─── Deck CRUD ─────────────────────────────────────────

@router.post("", response_model=DeckResponse, status_code=status.HTTP_201_CREATED)
def create_deck(
    request: DeckCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new deck for the authenticated user."""
    deck = Deck(
        user_id=user.id,
        name=request.name,
        format=request.format,
        description=request.description,
    )
    db.add(deck)
    db.commit()
    db.refresh(deck)
    return deck


@router.get("", response_model=list[DeckResponse])
def list_decks(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all decks belonging to the authenticated user."""
    return db.query(Deck).filter(Deck.user_id == user.id).order_by(Deck.updated_at.desc()).all()


@router.get("/{deck_id}", response_model=DeckDetailResponse)
def get_deck(
    deck_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a deck with all its cards."""
    deck = _get_user_deck(deck_id, user, db)
    return deck


@router.put("/{deck_id}", response_model=DeckResponse)
def update_deck(
    deck_id: UUID,
    request: DeckUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update deck name, format, or description."""
    deck = _get_user_deck(deck_id, user, db)

    if request.name is not None:
        deck.name = request.name
    if request.format is not None:
        deck.format = request.format
    if request.description is not None:
        deck.description = request.description

    db.commit()
    db.refresh(deck)
    return deck


@router.delete("/{deck_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_deck(
    deck_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a deck and all its cards."""
    deck = _get_user_deck(deck_id, user, db)
    db.delete(deck)
    db.commit()


# ─── Card Management ──────────────────────────────────

@router.post("/{deck_id}/cards", response_model=DeckCardResponse, status_code=status.HTTP_201_CREATED)
def add_card(
    deck_id: UUID,
    request: CardAdd,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Add a card to the deck.
    If the same card (same scryfall_id + board) already exists,
    the quantity is increased instead of creating a duplicate.
    """
    deck = _get_user_deck(deck_id, user, db)

    # Check if card already in deck on the same board
    existing = db.query(DeckCard).filter(
        DeckCard.deck_id == deck.id,
        DeckCard.scryfall_id == request.scryfall_id,
        DeckCard.board == request.board,
    ).first()

    if existing:
        existing.quantity += request.quantity
        db.commit()
        db.refresh(existing)
        return existing

    card = DeckCard(
        deck_id=deck.id,
        scryfall_id=request.scryfall_id,
        card_name=request.card_name,
        quantity=request.quantity,
        board=request.board,
    )
    db.add(card)
    db.commit()
    db.refresh(card)
    return card


@router.put("/{deck_id}/cards/{card_id}", response_model=DeckCardResponse)
def update_card(
    deck_id: UUID,
    card_id: UUID,
    request: CardUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a card's quantity or board (main/sideboard/commander)."""
    deck = _get_user_deck(deck_id, user, db)

    card = db.query(DeckCard).filter(
        DeckCard.id == card_id,
        DeckCard.deck_id == deck.id,
    ).first()

    if not card:
        raise HTTPException(status_code=404, detail="Card not found in this deck")

    if request.quantity is not None:
        if request.quantity <= 0:
            db.delete(card)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_200_OK,
                detail="Card removed (quantity set to 0)",
            )
        card.quantity = request.quantity

    if request.board is not None:
        card.board = request.board

    db.commit()
    db.refresh(card)
    return card


@router.delete("/{deck_id}/cards/{card_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_card(
    deck_id: UUID,
    card_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Remove a card from the deck entirely."""
    deck = _get_user_deck(deck_id, user, db)

    card = db.query(DeckCard).filter(
        DeckCard.id == card_id,
        DeckCard.deck_id == deck.id,
    ).first()

    if not card:
        raise HTTPException(status_code=404, detail="Card not found in this deck")

    db.delete(card)
    db.commit()