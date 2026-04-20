import asyncio
import time
from database.session import SessionLocal
from models.user import User
from models.deck import Deck
from models.deck_card import DeckCard
from services.scryfall import scryfall_service
from simulation.sim_tags import generate_sim_tags
from simulation.game_engine import run_simulation

async def test():
    db = SessionLocal()
    user = db.query(User).filter(User.email == "test@mtg.com").first()
    deck = db.query(Deck).filter(Deck.user_id == user.id).first()
    cards = db.query(DeckCard).filter(DeckCard.deck_id == deck.id).all()

    # Step 1: Fetch Scryfall data
    t0 = time.time()
    identifiers = [{"id": card.scryfall_id} for card in cards]
    scryfall_data = await scryfall_service.get_collection(identifiers)
    card_lookup = {c["id"]: c for c in scryfall_data.get("data", [])}
    t1 = time.time()
    print(f"Scryfall fetch: {t1-t0:.1f}s")

    # Build main deck
    main_deck = []
    for dc in cards:
        if dc.board != "main":
            continue
        cd = card_lookup.get(dc.scryfall_id)
        if cd:
            main_deck.append({"card_data": cd, "quantity": dc.quantity})

    # Step 2: Generate sim tags
    t2 = time.time()
    sim_tags = generate_sim_tags(cards, card_lookup)
    t3 = time.time()
    print(f"Sim tag generation: {t3-t2:.1f}s")
    print(f"  Tags generated for {len(sim_tags)} cards")

    # Step 3: Run simulation
    t4 = time.time()
    result = run_simulation(main_deck, sim_tags, n_games=10, turns=10)
    t5 = time.time()
    print(f"Simulation (10 games): {t5-t4:.1f}s")

    print(f"\nTotal: {t5-t0:.1f}s")
    db.close()

asyncio.run(test())