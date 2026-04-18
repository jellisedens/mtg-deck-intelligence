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
    
    print("Running full role classification...")
    role_data = classify_deck_roles(cards, card_lookup, {
        "name": deck.name,
        "format": deck.format,
        "description": deck.description,
    })
    
    print(f"\nPrimary creature type: {role_data['primary_creature_type']}")
    print(f"\nRole distribution:")
    for role, count in sorted(role_data["role_distribution"].items(), key=lambda x: -x[1]):
        if count > 0:
            print(f"  {role}: {count}")
    
    print(f"\nDragon-related cards:")
    for cr in role_data["card_roles"]:
        if "dragon" in cr["name"].lower():
            print(f"  {cr['name']}: primary={cr['primary_role']}, secondary={cr.get('secondary_roles', [])}")
            print(f"    synergy: {cr.get('synergy_notes', '')}")
    
    db.close()

asyncio.run(test())