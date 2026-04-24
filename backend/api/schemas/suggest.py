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
    impact_score: Optional[int] = None


class ClarificationOption(BaseModel):
    label: str
    description: str


class ClarificationResponse(BaseModel):
    needs_clarification: bool = True
    question: str
    options: list[ClarificationOption]

class SuggestResponse(BaseModel):
    # Normal response fields
    summary: Optional[str] = None
    suggestions: list[CardSuggestion] = []
    cuts: list[CutSuggestion] = []
    strategy_notes: Optional[str] = None
    # Clarification fields
    needs_clarification: bool = False
    clarification_question: Optional[str] = None
    clarification_options: list[ClarificationOption] = []
    #Debug info
    debug: Optional[dict] = None