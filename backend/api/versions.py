from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import Optional

from database.session import get_db
from models.user import User
from models.deck import Deck
from models.deck_card import DeckCard
from models.deck_version import DeckVersion
from api.deps import get_current_user

router = APIRouter(prefix="/decks", tags=["versions"])


class CreateVersionRequest(BaseModel):
    name: Optional[str] = None


class VersionSummary(BaseModel):
    id: str
    version_number: int
    name: Optional[str]
    card_count: int
    created_at: str

    class Config:
        from_attributes = True


class VersionDetail(BaseModel):
    id: str
    version_number: int
    name: Optional[str]
    card_snapshot: list
    analytics_snapshot: Optional[dict]
    strategy_snapshot: Optional[dict]
    created_at: str

    class Config:
        from_attributes = True


def _get_user_deck(deck_id: UUID, user: User, db: Session) -> Deck:
    deck = db.query(Deck).filter(Deck.id == deck_id).first()
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")
    if deck.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your deck")
    return deck


def _build_card_snapshot(deck_id: UUID, db: Session) -> list:
    """Build a snapshot of the current card list."""
    cards = db.query(DeckCard).filter(DeckCard.deck_id == deck_id).all()
    return [
        {
            "scryfall_id": c.scryfall_id,
            "card_name": c.card_name,
            "quantity": c.quantity,
            "board": c.board,
        }
        for c in cards
    ]


@router.post("/{deck_id}/versions", status_code=status.HTTP_201_CREATED)
async def create_version(
    deck_id: UUID,
    request: CreateVersionRequest = CreateVersionRequest(),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a snapshot of the current deck state with analytics and simulation."""
    deck = _get_user_deck(deck_id, user, db)

    # Get next version number
    max_version = db.query(func.max(DeckVersion.version_number)).filter(
        DeckVersion.deck_id == deck.id
    ).scalar() or 0

    # Card snapshot
    card_snapshot = _build_card_snapshot(deck.id, db)
    cards = db.query(DeckCard).filter(DeckCard.deck_id == deck.id).all()

    # Run analytics
    from services.analytics import compute_analytics
    analytics = await compute_analytics(cards, include_card_data=True)
    card_lookup = analytics.pop("_card_lookup", {})

    analytics_snapshot = {
        "total_cards": analytics.get("total_cards"),
        "average_cmc": analytics.get("average_cmc"),
        "mana_curve": analytics.get("mana_curve"),
        "type_distribution": analytics.get("type_distribution"),
        "color_distribution": analytics.get("color_distribution"),
        "mana_base": analytics.get("mana_base"),
    }

    # Run 1000-game simulation
    from simulation.game_engine import run_simulation
    main_deck_cards = []
    for card in cards:
        if card.board == "commander":
            continue
        card_data = card_lookup.get(card.scryfall_id)
        if card_data:
            main_deck_cards.append({"card_data": card_data, "quantity": card.quantity})

    sim_results = {}
    if main_deck_cards:
        # Get sim tags from profile if available
        sim_tags = (deck.strategy_profile or {}).get("sim_tags", {})
        sim_results = run_simulation(
            deck_cards=main_deck_cards, sim_tags=sim_tags, n_games=1000, turns=10,
        )

    analytics_snapshot["simulation"] = {
        "games_simulated": sim_results.get("games_simulated", 0),
        "mana_on_curve": sim_results.get("per_turn", {}).get("mana_on_curve_pct", {}),
        "avg_lands_by_turn": sim_results.get("per_turn", {}).get("avg_lands", {}),
        "avg_spells_cast_by_turn": sim_results.get("per_turn", {}).get("avg_spells_cast", {}),
        "avg_power_on_board": sim_results.get("per_turn", {}).get("avg_power_on_board", {}),
    }

    # Color health
    if sim_results:
        from services.mana_analyzer import compute_color_health
        color_health = compute_color_health(sim_results, analytics)
        analytics_snapshot["color_health"] = color_health

    # Strategy snapshot
    strategy_snapshot = None
    if deck.strategy_profile:
        profile = deck.strategy_profile
        strategy_snapshot = {
            "primary_strategy": profile.get("primary_strategy"),
            "win_conditions": profile.get("win_conditions", []),
            "weaknesses": profile.get("weaknesses", []),
            "color_identity": profile.get("color_identity"),
            "role_distribution": (profile.get("role_data") or {}).get("role_distribution", {}),
        }

    version = DeckVersion(
        deck_id=deck.id,
        version_number=max_version + 1,
        name=request.name,
        card_snapshot=card_snapshot,
        analytics_snapshot=analytics_snapshot,
        strategy_snapshot=strategy_snapshot,
    )

    db.add(version)
    db.commit()
    db.refresh(version)

    return {
        "id": str(version.id),
        "version_number": version.version_number,
        "name": version.name,
        "card_count": len(card_snapshot),
        "average_cmc": analytics_snapshot.get("average_cmc"),
        "games_simulated": sim_results.get("games_simulated", 0),
        "created_at": version.created_at.isoformat(),
    }


@router.get("/{deck_id}/versions")
def list_versions(
    deck_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all versions for a deck."""
    deck = _get_user_deck(deck_id, user, db)

    versions = db.query(DeckVersion).filter(
        DeckVersion.deck_id == deck.id
    ).order_by(DeckVersion.version_number.desc()).all()

    return [
        {
            "id": str(v.id),
            "version_number": v.version_number,
            "name": v.name,
            "card_count": len(v.card_snapshot) if v.card_snapshot else 0,
            "created_at": v.created_at.isoformat(),
        }
        for v in versions
    ]


@router.get("/{deck_id}/versions/{version_id}")
def get_version(
    deck_id: UUID,
    version_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific version with full card snapshot."""
    deck = _get_user_deck(deck_id, user, db)

    version = db.query(DeckVersion).filter(
        DeckVersion.id == version_id,
        DeckVersion.deck_id == deck.id,
    ).first()

    if not version:
        raise HTTPException(status_code=404, detail="Version not found")

    return {
        "id": str(version.id),
        "version_number": version.version_number,
        "name": version.name,
        "card_snapshot": version.card_snapshot,
        "analytics_snapshot": version.analytics_snapshot,
        "strategy_snapshot": version.strategy_snapshot,
        "created_at": version.created_at.isoformat(),
    }


@router.post("/{deck_id}/versions/{version_id}/restore")
def restore_version(
    deck_id: UUID,
    version_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Restore a deck to a previous version. Auto-snapshots current state first."""
    deck = _get_user_deck(deck_id, user, db)

    version = db.query(DeckVersion).filter(
        DeckVersion.id == version_id,
        DeckVersion.deck_id == deck.id,
    ).first()

    if not version:
        raise HTTPException(status_code=404, detail="Version not found")

    # Auto-snapshot current state before restoring
    max_version = db.query(func.max(DeckVersion.version_number)).filter(
        DeckVersion.deck_id == deck.id
    ).scalar() or 0

    current_snapshot = _build_card_snapshot(deck.id, db)
    auto_version = DeckVersion(
        deck_id=deck.id,
        version_number=max_version + 1,
        name=f"Auto-save before restore to v{version.version_number}",
        card_snapshot=current_snapshot,
        strategy_snapshot={
            "primary_strategy": (deck.strategy_profile or {}).get("primary_strategy"),
            "win_conditions": (deck.strategy_profile or {}).get("win_conditions", []),
            "color_identity": (deck.strategy_profile or {}).get("color_identity"),
        } if deck.strategy_profile else None,
    )
    db.add(auto_version)

    # Delete current cards
    db.query(DeckCard).filter(DeckCard.deck_id == deck.id).delete()

    # Restore cards from snapshot
    for card_data in version.card_snapshot:
        card = DeckCard(
            deck_id=deck.id,
            scryfall_id=card_data["scryfall_id"],
            card_name=card_data["card_name"],
            quantity=card_data.get("quantity", 1),
            board=card_data.get("board", "main"),
        )
        db.add(card)

    # Mark strategy as stale since cards changed
    if deck.strategy_profile:
        from sqlalchemy.orm.attributes import flag_modified
        deck.strategy_profile["simulation_stale"] = True
        deck.strategy_profile["cards_changed_since_regen"] = len(version.card_snapshot)
        flag_modified(deck, "strategy_profile")

    db.commit()

    return {
        "status": "restored",
        "restored_to": version.version_number,
        "auto_saved_as": max_version + 1,
        "cards_restored": len(version.card_snapshot),
    }


@router.get("/{deck_id}/versions/{version_id}/diff")
def compare_version(
    deck_id: UUID,
    version_id: UUID,
    compare_to: UUID = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Compare a version against current deck or another version."""
    deck = _get_user_deck(deck_id, user, db)

    version = db.query(DeckVersion).filter(
        DeckVersion.id == version_id,
        DeckVersion.deck_id == deck.id,
    ).first()

    if not version:
        raise HTTPException(status_code=404, detail="Version not found")

    # Build "before" cards from this version
    before_cards = {}
    for c in version.card_snapshot:
        before_cards[c["card_name"].lower()] = {
            "card_name": c["card_name"],
            "quantity": c.get("quantity", 1),
            "board": c.get("board", "main"),
        }
    before_analytics = version.analytics_snapshot

    # Build "after" cards — either from another version or current deck
    if compare_to:
        other = db.query(DeckVersion).filter(
            DeckVersion.id == compare_to,
            DeckVersion.deck_id == deck.id,
        ).first()
        if not other:
            raise HTTPException(status_code=404, detail="Comparison version not found")
        after_cards = {}
        for c in other.card_snapshot:
            after_cards[c["card_name"].lower()] = {
                "card_name": c["card_name"],
                "quantity": c.get("quantity", 1),
                "board": c.get("board", "main"),
            }
        after_analytics = other.analytics_snapshot
        after_label = f"v{other.version_number}"
    else:
        after_cards = {}
        for c in db.query(DeckCard).filter(DeckCard.deck_id == deck.id).all():
            after_cards[c.card_name.lower()] = {
                "card_name": c.card_name,
                "quantity": c.quantity,
                "board": c.board,
            }
        # Current analytics from strategy profile
        profile = deck.strategy_profile or {}
        after_analytics = {
            "average_cmc": None,
            "total_cards": sum(c["quantity"] for c in after_cards.values()),
            "simulation": profile.get("cached_simulation"),
            "color_health": profile.get("color_health"),
            "mana_curve": None,
        }
        after_label = "current"

    # Compute card diff
    added = []
    removed = []
    changed = []

    for name, card in after_cards.items():
        if name not in before_cards:
            added.append(card)
        elif card["quantity"] != before_cards[name]["quantity"] or card["board"] != before_cards[name]["board"]:
            changed.append({
                "card_name": card["card_name"],
                "before": {"quantity": before_cards[name]["quantity"], "board": before_cards[name]["board"]},
                "after": {"quantity": card["quantity"], "board": card["board"]},
            })

    for name, card in before_cards.items():
        if name not in after_cards:
            removed.append(card)

    # Analytics comparison
    analytics_comparison = None
    if before_analytics or after_analytics:
        before_a = before_analytics or {}
        after_a = after_analytics or {}
        
        before_sim = before_a.get("simulation", {}) or {}
        after_sim = after_a.get("simulation", {}) or {}

        analytics_comparison = {
            "before": {
                "label": f"v{version.version_number}",
                "average_cmc": before_a.get("average_cmc"),
                "total_cards": before_a.get("total_cards"),
                "mana_curve": before_a.get("mana_curve"),
                "games_simulated": before_sim.get("games_simulated", 0),
                "mana_on_curve": before_sim.get("mana_on_curve_pct"),
                "color_health": before_a.get("color_health"),
            },
            "after": {
                "label": after_label,
                "average_cmc": after_a.get("average_cmc"),
                "total_cards": after_a.get("total_cards"),
                "mana_curve": after_a.get("mana_curve"),
                "games_simulated": after_sim.get("games_simulated", 0),
                "mana_on_curve": after_sim.get("mana_on_curve_pct"),
                "color_health": after_a.get("color_health"),
            },
        }

    return {
        "before_label": f"v{version.version_number}",
        "after_label": after_label,
        "before_card_count": len(before_cards),
        "after_card_count": len(after_cards),
        "added": added,
        "removed": removed,
        "changed": changed,
        "analytics": analytics_comparison,
    }

@router.delete("/{deck_id}/versions/{version_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_version(
    deck_id: UUID,
    version_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a version snapshot."""
    deck = _get_user_deck(deck_id, user, db)

    version = db.query(DeckVersion).filter(
        DeckVersion.id == version_id,
        DeckVersion.deck_id == deck.id,
    ).first()

    if not version:
        raise HTTPException(status_code=404, detail="Version not found")

    db.delete(version)
    db.commit()