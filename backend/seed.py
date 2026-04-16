"""
Seed script — clears existing seed data and creates fresh test data.
Run inside the container:
    docker exec -it mtg-backend python seed.py
"""

from database.session import SessionLocal
from models.user import User
from models.deck import Deck
from models.deck_card import DeckCard
from models.simulation_result import SimulationResult
from services.auth import hash_password

SEED_EMAIL = "test@mtg.com"
SEED_PASSWORD = "password123"


def clear_seed_data(db):
    """Remove all data created by previous seeds."""
    user = db.query(User).filter(User.email == SEED_EMAIL).first()
    if not user:
        print("No existing seed data found")
        return

    # Delete in order: cards/simulations → decks → user
    for deck in db.query(Deck).filter(Deck.user_id == user.id).all():
        db.query(DeckCard).filter(DeckCard.deck_id == deck.id).delete()
        db.query(SimulationResult).filter(SimulationResult.deck_id == deck.id).delete()
        db.delete(deck)

    db.delete(user)
    db.commit()
    print("Cleared existing seed data")


def seed():
    db = SessionLocal()

    # --- Always start fresh ---
    clear_seed_data(db)

    # --- Create test user ---
    user = User(
        email=SEED_EMAIL,
        password_hash=hash_password(SEED_PASSWORD),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    print(f"Created test user: {user.id}")

    # --- Seed decks ---
    import data.ur_dragon_edh as ur_dragon
    seed_deck(db, user, ur_dragon)

    # Future decks:
    # import data.mono_red_aggro as mono_red
    # seed_deck(db, user, mono_red)

    db.close()
    print(f"\nSeed complete!")
    print(f"  Login: {SEED_EMAIL} / {SEED_PASSWORD}")


def seed_deck(db, user, deck_module):
    """Seed a single deck from a data module."""
    deck = Deck(
        user_id=user.id,
        name=deck_module.DECK_NAME,
        format=deck_module.DECK_FORMAT,
        description=deck_module.DECK_DESCRIPTION,
    )
    db.add(deck)
    db.commit()
    db.refresh(deck)

    count = 0
    for card_name, scryfall_id, quantity, board in deck_module.CARDS:
        card = DeckCard(
            deck_id=deck.id,
            scryfall_id=scryfall_id,
            card_name=card_name,
            quantity=quantity,
            board=board,
        )
        db.add(card)
        count += quantity

    db.commit()
    print(f"  Created '{deck.name}' — {count} cards ({len(deck_module.CARDS)} unique)")


if __name__ == "__main__":
    seed()