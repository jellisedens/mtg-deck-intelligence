from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.session import get_db
from models.user import User
from models.deck import Deck
from models.deck_card import DeckCard
from api.deps import get_current_user
from services.scryfall import scryfall_service
from simulation.sim_tags import generate_sim_tags
from simulation.hand_simulator import simulate_opening_hands, simulate_mulligan_sequence
from simulation.game_engine import run_simulation
from services.simulation_analyzer import analyze_simulation

router = APIRouter(prefix="/decks", tags=["simulation"])

# Simple in-memory cache for sim tags (avoids regenerating on every call)
_sim_tag_cache = {}

async def _build_deck_for_simulation(deck_id: UUID, user: User, db: Session) -> tuple:
    """Fetch deck cards and their Scryfall data, generate sim tags."""
    deck = db.query(Deck).filter(Deck.id == deck_id).first()
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")
    if deck.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your deck")

    deck_cards = db.query(DeckCard).filter(DeckCard.deck_id == deck.id).all()
    if not deck_cards:
        raise HTTPException(status_code=400, detail="Deck has no cards")

    # Fetch full card data from Scryfall
    identifiers = [{"id": card.scryfall_id} for card in deck_cards]
    scryfall_data = await scryfall_service.get_collection(identifiers)

    if "error" in scryfall_data:
        raise HTTPException(status_code=502, detail="Failed to fetch card data from Scryfall")

    card_lookup = {c["id"]: c for c in scryfall_data.get("data", [])}

    # Build card list
    main_deck_cards = []
    for deck_card in deck_cards:
        if deck_card.board != "main":
            continue
        card_data = card_lookup.get(deck_card.scryfall_id)
        if card_data:
            main_deck_cards.append({
                "card_data": card_data,
                "quantity": deck_card.quantity,
            })

   # Generate simulation tags (cached per deck)
    cache_key = str(deck_id)
    if cache_key in _sim_tag_cache:
        sim_tags = _sim_tag_cache[cache_key]
    else:
        sim_tags = generate_sim_tags(deck_cards, card_lookup)
        _sim_tag_cache[cache_key] = sim_tags

    return main_deck_cards, sim_tags


@router.post("/{deck_id}/simulate/hand")
async def simulate_hand(
    deck_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    n_simulations: int = 1000,
    mulligan_to: int = 7,
):
    """
    Simulate drawing opening hands N times.
    Returns probability distributions for lands, card types,
    colors, and playability metrics.
    """
    if n_simulations < 1 or n_simulations > 10000:
        raise HTTPException(status_code=400, detail="Simulations must be between 1 and 10000")

    main_deck, sim_tags = await _build_deck_for_simulation(deck_id, user, db)

    result = simulate_opening_hands(
        cards=main_deck,
        n_simulations=n_simulations,
        mulligan_to=mulligan_to,
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@router.post("/{deck_id}/simulate/mulligan")
async def simulate_mulligans(
    deck_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Simulate the London mulligan decision process.
    Shows how often you need to mulligan and average final hand size.
    """
    main_deck, sim_tags = await _build_deck_for_simulation(deck_id, user, db)

    result = simulate_mulligan_sequence(
        cards=main_deck,
        n_simulations=1000,
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@router.post("/{deck_id}/simulate/game")
async def simulate_games(
    deck_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    n_games: int = 100,
    turns: int = 10,
):
    """
    Simulate N goldfish games over multiple turns.
    Returns averaged per-turn statistics including mana development,
    board state, castability, and on-curve rates.
    """
    if n_games < 1 or n_games > 1000:
        raise HTTPException(status_code=400, detail="Games must be between 1 and 1000")
    if turns < 1 or turns > 15:
        raise HTTPException(status_code=400, detail="Turns must be between 1 and 15")

    main_deck, sim_tags = await _build_deck_for_simulation(deck_id, user, db)

    result = run_simulation(
        deck_cards=main_deck,
        sim_tags=sim_tags,
        n_games=n_games,
        turns=turns,
    )

    return result

@router.post("/{deck_id}/simulate/analyze")
async def simulate_and_analyze(
    deck_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    n_games: int = 100,
    turns: int = 10,
):
    """
    Convenience endpoint: runs simulation + AI analysis in one call.
    Equivalent to calling /simulate/game then /simulate/interpret.
    """
    if n_games < 1 or n_games > 1000:
        raise HTTPException(status_code=400, detail="Games must be between 1 and 1000")

    deck = db.query(Deck).filter(Deck.id == deck_id).first()
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")

    main_deck, sim_tags = await _build_deck_for_simulation(deck_id, user, db)

    sim_results = run_simulation(
        deck_cards=main_deck,
        sim_tags=sim_tags,
        n_games=n_games,
        turns=turns,
    )

    deck_info = {
        "name": deck.name,
        "format": deck.format,
        "description": deck.description,
    }

    analysis = analyze_simulation(
        simulation_data=sim_results,
        deck_info=deck_info,
        strategy_profile=deck.strategy_profile,
    )

    return {
        "simulation": sim_results,
        "analysis": analysis,
    }

@router.post("/{deck_id}/simulate/interpret")
async def interpret_simulation(
    deck_id: UUID,
    simulation_data: dict,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Interpret existing simulation results with AI analysis.
    Pass in the raw output from /simulate/game — no re-simulation needed.
    """
    deck = db.query(Deck).filter(Deck.id == deck_id).first()
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")
    if deck.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your deck")

    deck_info = {
        "name": deck.name,
        "format": deck.format,
        "description": deck.description,
    }

    analysis = analyze_simulation(
        simulation_data=simulation_data,
        deck_info=deck_info,
        strategy_profile=deck.strategy_profile,
    )

    if "error" in analysis:
        raise HTTPException(status_code=502, detail=f"Analysis failed: {analysis['error']}")

    return analysis

@router.post("/{deck_id}/simulate/regenerate-tags")
async def regenerate_sim_tags_endpoint(
    deck_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Force regeneration of simulation tags for a deck.
    Use this after making changes to the deck's cards.
    """
    deck = db.query(Deck).filter(Deck.id == deck_id).first()
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")
    if deck.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your deck")

    deck_cards = db.query(DeckCard).filter(DeckCard.deck_id == deck.id).all()

    identifiers = [{"id": card.scryfall_id} for card in deck_cards]
    scryfall_data = await scryfall_service.get_collection(identifiers)
    card_lookup = {c["id"]: c for c in scryfall_data.get("data", [])}

    sim_tags = generate_sim_tags(deck_cards, card_lookup)

    profile = deck.strategy_profile or {}
    profile["sim_tags"] = sim_tags
    deck.strategy_profile = profile
    db.commit()

    return {"status": "ok", "tags_generated": len(sim_tags)}