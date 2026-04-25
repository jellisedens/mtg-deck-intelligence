"""
Deck import endpoints.
Supports importing from Archidekt URLs and plain text lists.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from database.session import get_db
from models.user import User
from models.deck import Deck
from models.deck_card import DeckCard
from api.deps import get_current_user
from services.deck_import import import_from_archidekt, import_from_text

router = APIRouter(prefix="/decks", tags=["deck import"])


class ArchidektImportRequest(BaseModel):
    url: str
    name_override: Optional[str] = None
    format_override: Optional[str] = None


class TextImportRequest(BaseModel):
    deck_text: str
    name: str = "Imported Deck"
    format: str = "commander"
    description: str = ""


class ImportResponse(BaseModel):
    deck_id: str
    name: str
    format: str
    cards_imported: int
    cards_failed: int
    errors: list[str] = []


@router.post("/import/archidekt", response_model=ImportResponse)
async def import_archidekt_deck(
    request: ArchidektImportRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Import a deck from Archidekt.
    Provide the full URL (https://archidekt.com/decks/123456) or just the deck ID.
    """
    result = await import_from_archidekt(request.url)

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    # Create the deck
    deck_name = request.name_override or result["name"]
    deck_format = request.format_override or result["format"]

    deck = Deck(
        user_id=user.id,
        name=deck_name,
        format=deck_format,
        description=result.get("description", ""),
    )
    db.add(deck)
    db.flush()  # Get deck ID without committing

    # Add all cards
    cards_imported = 0
    for card in result["cards"]:
        deck_card = DeckCard(
            deck_id=deck.id,
            scryfall_id=card["scryfall_id"],
            card_name=card["card_name"],
            quantity=card["quantity"],
            board=card["board"],
        )
        db.add(deck_card)
        cards_imported += 1

    db.commit()

    return ImportResponse(
        deck_id=str(deck.id),
        name=deck_name,
        format=deck_format,
        cards_imported=cards_imported,
        cards_failed=len(result.get("errors", [])),
        errors=result.get("errors", []),
    )


@router.post("/import/text", response_model=ImportResponse)
async def import_text_deck(
    request: TextImportRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Import a deck from a plain text list.
    Format: one card per line, e.g.:
        1x Sol Ring
        1x Command Tower
        1x The Ur-Dragon *CMDR*
    
    Section headers:
        // Commander
        // Sideboard
    """
    result = await import_from_text(request.deck_text, request.format)

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    deck = Deck(
        user_id=user.id,
        name=request.name,
        format=request.format,
        description=request.description,
    )
    db.add(deck)
    db.flush()

    cards_imported = 0
    for card in result["cards"]:
        deck_card = DeckCard(
            deck_id=deck.id,
            scryfall_id=card["scryfall_id"],
            card_name=card["card_name"],
            quantity=card["quantity"],
            board=card["board"],
        )
        db.add(deck_card)
        cards_imported += 1

    db.commit()

    return ImportResponse(
        deck_id=str(deck.id),
        name=request.name,
        format=request.format,
        cards_imported=cards_imported,
        cards_failed=len(result.get("errors", [])),
        errors=result.get("errors", []),
    )