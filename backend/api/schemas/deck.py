from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional


# --- Deck ---

class DeckCreate(BaseModel):
    name: str
    format: str = "commander"
    description: Optional[str] = None


class DeckUpdate(BaseModel):
    name: Optional[str] = None
    format: Optional[str] = None
    description: Optional[str] = None


class DeckPreferences(BaseModel):
    """User-defined deck intent and constraints."""
    strategy_notes: Optional[str] = None
    color_preferences: Optional[str] = None
    card_type_preferences: Optional[str] = None
    budget: Optional[str] = None
    other_notes: Optional[str] = None


class DeckCardResponse(BaseModel):
    id: UUID
    scryfall_id: str
    card_name: str
    quantity: int
    board: str

    class Config:
        from_attributes = True


class DeckResponse(BaseModel):
    id: UUID
    name: str
    format: str
    description: Optional[str]
    preferences: Optional[dict] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DeckDetailResponse(DeckResponse):
    """Deck with its cards included."""
    cards: list[DeckCardResponse] = []


# --- Deck Cards ---

class CardAdd(BaseModel):
    scryfall_id: str
    card_name: str
    quantity: int = 1
    board: str = "main"


class CardUpdate(BaseModel):
    quantity: Optional[int] = None
    board: Optional[str] = None