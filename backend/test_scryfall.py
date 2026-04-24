import time
import asyncio
from services.scryfall import scryfall_service
from database.session import SessionLocal
from models.deck_card import DeckCard

db = SessionLocal()
cards = db.query(DeckCard).all()
identifiers = [{"id": card.scryfall_id} for card in cards]
print(f"Fetching {len(identifiers)} cards...")

async def test():
    t = time.time()
    result = await scryfall_service.get_collection(identifiers)
    elapsed = time.time() - t
    count = len(result.get("data", []))
    print(f"Collection call: {elapsed:.1f}s")
    print(f"Cards returned: {count}")

asyncio.run(test())