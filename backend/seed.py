"""
Seed script — clears existing seed data and creates fresh test data.
Uses Scryfall's collection endpoint to batch-resolve card IDs.
Run inside the container:
    docker exec -it mtg-backend python seed.py
"""

import asyncio
from database.session import SessionLocal
from models.user import User
from models.deck import Deck
from models.deck_card import DeckCard
from models.simulation_result import SimulationResult
from services.auth import hash_password
from services.scryfall import scryfall_service

SEED_EMAIL = "test@mtg.com"
SEED_PASSWORD = "password123"


def clear_seed_data(db):
    """Remove all data created by previous seeds."""
    user = db.query(User).filter(User.email == SEED_EMAIL).first()
    if not user:
        print("No existing seed data found")
        return

    for deck in db.query(Deck).filter(Deck.user_id == user.id).all():
        db.query(DeckCard).filter(DeckCard.deck_id == deck.id).delete()
        db.query(SimulationResult).filter(SimulationResult.deck_id == deck.id).delete()
        db.delete(deck)

    db.delete(user)
    db.commit()
    print("Cleared existing seed data")


async def resolve_scryfall_ids(cards_data):
    """Batch-resolve real Scryfall IDs using the collection endpoint, with fallback."""
    # Build identifiers — use name-based lookup
    identifiers = [{"name": card_name} for card_name, _, _, _ in cards_data]

    print(f"  Fetching {len(identifiers)} cards from Scryfall...")
    result = await scryfall_service.get_collection(identifiers)

    if "error" in result:
        print(f"  ERROR: {result['error']} — {result.get('details')}")
        return [], [c[0] for c in cards_data]

    # Build lookup: card name (lowercase) → scryfall data
    found_lookup = {}
    for card in result.get("data", []):
        found_lookup[card["name"].lower()] = card

    # Match back to our card list
    resolved = []
    failed = []

    for card_name, _, quantity, board in cards_data:
        scryfall_card = found_lookup.get(card_name.lower())
        if scryfall_card:
            resolved.append((card_name, scryfall_card["id"], quantity, board))
        else:
            failed.append((card_name, quantity, board))

    # Fallback: resolve failed cards individually by name
    if failed:
        print(f"  Resolving {len(failed)} remaining cards individually...")
        still_failed = []
        for card_name, quantity, board in failed:
            result = await scryfall_service.get_card_by_name(card_name, fuzzy=False)
            if "error" not in result:
                resolved.append((card_name, result["id"], quantity, board))
            else:
                # Try fuzzy
                result = await scryfall_service.get_card_by_name(card_name, fuzzy=True)
                if "error" not in result:
                    resolved.append((card_name, result["id"], quantity, board))
                else:
                    still_failed.append(card_name)
        failed = still_failed

    return resolved, failed


def seed_deck_sync(db, user, deck_module):
    """Seed a single deck, resolving Scryfall IDs via collection endpoint."""
    deck = Deck(
        user_id=user.id,
        name=deck_module.DECK_NAME,
        format=deck_module.DECK_FORMAT,
        description=deck_module.DECK_DESCRIPTION,
    )
    db.add(deck)
    db.commit()
    db.refresh(deck)

    resolved, failed = asyncio.run(resolve_scryfall_ids(deck_module.CARDS))

    if failed:
        print(f"  WARNING: {len(failed)} cards not found:")
        for name in failed:
            print(f"    - {name}")

    count = 0
    for card_name, scryfall_id, quantity, board in resolved:
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
    print(f"  Created '{deck.name}' — {count} cards ({len(resolved)} resolved, {len(failed)} failed)")


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
    seed_deck_sync(db, user, ur_dragon)

    db.close()
    print(f"\nSeed complete!")
    print(f"  Login: {SEED_EMAIL} / {SEED_PASSWORD}")


if __name__ == "__main__":
    seed()