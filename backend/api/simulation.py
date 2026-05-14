from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from simulation.custom_metrics import compute_custom_metrics
from pydantic import BaseModel
from typing import Optional
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

class CustomTrackingRequest(BaseModel):
    track_roles: Optional[list[str]] = None
    track_types: Optional[list[str]] = None
    track_commander: Optional[dict] = None
    track_cmc_slots: Optional[list[int]] = None

router = APIRouter(prefix="/decks", tags=["simulation"])

# Simple in-memory cache for sim tags (avoids regenerating on every call)
_sim_tag_cache = {}

async def _build_deck_for_simulation(deck_id: UUID, user: User, db: Session) -> tuple:
    """Fetch deck cards and their Scryfall data, use cached sim tags from strategy profile."""
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

    # Use cached sim tags from strategy profile first, then in-memory cache, then generate
    sim_tags = None
    if deck.strategy_profile and deck.strategy_profile.get("sim_tags"):
        sim_tags = deck.strategy_profile["sim_tags"]
    elif str(deck_id) in _sim_tag_cache:
        sim_tags = _sim_tag_cache[str(deck_id)]
    else:
        # Only generate if no cache exists anywhere — this is the slow path
        sim_tags = generate_sim_tags(deck_cards, card_lookup)
        _sim_tag_cache[str(deck_id)] = sim_tags

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
    min_lands: int = 2,
    max_lands: int = 5,
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
        min_lands=min_lands,
        max_lands=max_lands,
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

@router.post("/{deck_id}/simulate/custom")
async def simulate_with_custom_tracking(
    deck_id: UUID,
    tracking: CustomTrackingRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    n_games: int = 500,
    turns: int = 10,
):
    """Run simulation with custom metric tracking."""
    if n_games < 1 or n_games > 1000:
        raise HTTPException(status_code=400, detail="Games must be between 1 and 1000")

    main_deck, sim_tags = await _build_deck_for_simulation(deck_id, user, db)

    # Run simulation once — reuse raw games for custom metrics
    standard_results = run_simulation(
        deck_cards=main_deck,
        sim_tags=sim_tags,
        n_games=n_games,
        turns=turns,
    )
    
    # Extract raw games for custom metrics, then remove from response
    all_games = standard_results.pop("_raw_games", [])

    # Compute custom metrics
    tracking_options = tracking.model_dump(exclude_none=True)
    
    # Auto-detect commander for castability tracking
    if tracking_options.get("track_commander") is not None:
        deck = db.query(Deck).filter(Deck.id == deck_id).first()
        commander_cards = db.query(DeckCard).filter(
            DeckCard.deck_id == deck_id,
            DeckCard.board == "commander",
        ).all()
        if commander_cards:
            cmd_card = commander_cards[0]
            # Find commander data in the fetched card data
            for card_entry in main_deck:
                pass  # main_deck only has non-commander cards
            # Fetch commander data from Scryfall
            cmd_identifiers = [{"id": cmd_card.scryfall_id}]
            cmd_data_resp = await scryfall_service.get_collection(cmd_identifiers)
            cmd_data_list = cmd_data_resp.get("data", [])
            if cmd_data_list:
                cmd_data = cmd_data_list[0]
                cmd_cmc = int(cmd_data.get("cmc", 0))
                # Parse color requirements from mana cost
                mana_cost = cmd_data.get("mana_cost", "")
                color_reqs = {}
                for color in ["W", "U", "B", "R", "G"]:
                    count = mana_cost.count("{" + color + "}")
                    if count > 0:
                        color_reqs[color] = count
                tracking_options["track_commander"] = {
                    "cmc": cmd_cmc,
                    "colors": color_reqs,
                    "name": cmd_data.get("name", "Commander"),
                }
            else:
                del tracking_options["track_commander"]
        else:
            del tracking_options["track_commander"]
    # Build role map from user-tagged cards
    deck_cards_db = db.query(DeckCard).filter(DeckCard.deck_id == deck_id).all()
    user_role_map = {}
    for card in deck_cards_db:
        ai_ctx = card.ai_context or {}
        card_roles = ai_ctx.get("roles", [])
        if card_roles:
            user_role_map[card.card_name.lower()] = card_roles

    custom_metrics = compute_custom_metrics(
        all_games=all_games,
        tracking_options=tracking_options,
        deck_cards=main_deck,
        sim_tags=sim_tags,
        user_role_map=user_role_map,
    )

    standard_results["custom_metrics"] = custom_metrics
    return standard_results