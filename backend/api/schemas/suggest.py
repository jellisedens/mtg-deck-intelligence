from pydantic import BaseModel
from typing import Optional
from uuid import UUID


class SuggestRequest(BaseModel):
    prompt: str
    deck_id: Optional[UUID] = None


class CardSuggestion(BaseModel):
    card_name: str
    scryfall_id: Optional[str] = None
    reasoning: str
    category: Optional[str] = None
    priority: Optional[str] = None
    budget_note: Optional[str] = None
    image_uri: Optional[str] = None
    mana_cost: Optional[str] = None
    type_line: Optional[str] = None
    price_usd: Optional[str] = None


class CutSuggestion(BaseModel):
    card_name: str
    reasoning: str


class SuggestResponse(BaseModel):
    summary: str
    suggestions: list[CardSuggestion] = []
    cuts: list[CutSuggestion] = []
    strategy_notes: Optional[str] = None