from pydantic import BaseModel
from typing import Optional


class ColorInfo(BaseModel):
    name: str
    count: int


class ManaBase(BaseModel):
    land_count: int
    non_land_count: int
    land_percentage: float
    color_sources: dict[str, int]


class Composition(BaseModel):
    main: int
    sideboard: int
    commander: int
    total: int


class AnalyticsResponse(BaseModel):
    total_cards: int
    unique_cards: int
    cards_not_found: list[str]
    mana_curve: dict[str, int]
    color_distribution: dict[str, ColorInfo]
    type_distribution: dict[str, int]
    mana_base: ManaBase
    average_cmc: float
    composition: Composition