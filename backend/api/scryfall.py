from fastapi import APIRouter, Query

from services.scryfall import scryfall_service
from pydantic import BaseModel

router = APIRouter(prefix="/scryfall", tags=["scryfall"])


@router.get("/search")
async def search_cards(
    q: str = Query(..., description="Search query using Scryfall syntax"),
    page: int = Query(1, description="Page number for paginated results"),
):
    """
    Search for Commander-legal cards using Scryfall syntax.
    Examples: 'sol ring', 'c:red t:creature cmc:3', 'o:draw t:instant'
    """
    return await scryfall_service.search_cards(q, page)


@router.get("/card/name")
async def get_card_by_name(
    name: str = Query(..., description="Card name"),
    fuzzy: bool = Query(False, description="Use fuzzy matching for misspellings"),
):
    """
    Get a single card by name.
    Use fuzzy=true for approximate matching (e.g. 'jac bele' finds 'Jace Beleren').
    """
    return await scryfall_service.get_card_by_name(name, fuzzy)


@router.get("/card/{scryfall_id}")
async def get_card_by_id(scryfall_id: str):
    """Get a single card by its Scryfall UUID."""
    return await scryfall_service.get_card_by_id(scryfall_id)


@router.get("/autocomplete")
async def autocomplete(
    q: str = Query(..., description="Partial card name for autocomplete"),
):
    """
    Get up to 20 card name suggestions as the user types.
    Fast endpoint for powering search-as-you-type UI.
    """
    return await scryfall_service.autocomplete(q)

class CollectionRequest(BaseModel):
    identifiers: list[dict]

@router.post("/collection")
async def get_collection(request: CollectionRequest):
    """
    Fetch multiple cards at once by Scryfall ID.
    Accepts up to 75 identifiers per batch (handled automatically).
    Each identifier should be {"id": "scryfall-uuid"}.
    """
    return await scryfall_service.get_collection(request.identifiers)