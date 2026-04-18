import asyncio
from database.session import SessionLocal
from models.user import User
from models.deck import Deck
from models.deck_card import DeckCard
from services.analytics import compute_analytics
from services.role_classifier import classify_deck_roles

async def test():
    db = SessionLocal()
    user = db.query(User).filter(User.email == "test@mtg.com").first()
    deck = db.query(Deck).filter(Deck.user_id == user.id).first()
    cards = db.query(DeckCard).filter(DeckCard.deck_id == deck.id).all()
    
    analytics = await compute_analytics(cards, include_card_data=True)
    card_lookup = analytics.pop("_card_lookup", {})
    
    role_data = classify_deck_roles(cards, card_lookup, {
        "name": deck.name,
        "format": deck.format,
        "description": deck.description,
    })
    
    # Find Dragonborn Champion and Dragon Tempest
    for cr in role_data["card_roles"]:
        if "dragon" in cr["name"].lower():
            print(f"  {cr['name']}: primary={cr['primary_role']}, secondary={cr.get('secondary_roles', [])}, synergy={cr.get('synergy_notes', '')}")
    
    db.close()

asyncio.run(test())