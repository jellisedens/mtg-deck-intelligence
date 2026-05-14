from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from services.deck_intelligence import log_card_added, log_card_removed
from database.session import get_db
from models.user import User
from models.deck import Deck
from models.deck_card import DeckCard
from api.deps import get_current_user
from api.schemas.deck import (
    DeckCreate,
    DeckUpdate,
    DeckResponse,
    DeckDetailResponse,
    CardAdd,
    CardUpdate,
    DeckCardResponse,
    DeckPreferences,
)

router = APIRouter(prefix="/decks", tags=["decks"])


# ─── Helpers ───────────────────────────────────────────

def _get_user_deck(deck_id: UUID, user: User, db: Session) -> Deck:
    """Fetch a deck and verify it belongs to the current user."""
    deck = db.query(Deck).filter(Deck.id == deck_id).first()

    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")
    if deck.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your deck")

    return deck


def _patch_strategy_card_added(deck: Deck, card_name: str, scryfall_id: str, card_data: dict = None):
    """Incrementally update strategy profile when a card is added.
    No AI calls — just data manipulation for instant updates."""
    profile = deck.strategy_profile
    if not profile:
        return

    type_line = (card_data or {}).get("type_line", "")
    oracle_text = (card_data or {}).get("oracle_text", "")
    mana_cost = (card_data or {}).get("mana_cost", "")

    # 1. Classify role for this single card (rule-based)
    role = _classify_single_card(type_line, oracle_text)

    # 2. Update role_data
    role_data = profile.get("role_data") or {}
    card_roles = role_data.get("card_roles", [])
    card_roles.append({
        "name": card_name,
        "card_name": card_name,
        "primary_role": role,
        "secondary_roles": [],
        "synergy": "Provisional — regenerate strategy for full analysis",
    })
    role_data["card_roles"] = card_roles

    dist = role_data.get("role_distribution", {})
    dist[role] = dist.get(role, 0) + 1
    role_data["role_distribution"] = dist
    profile["role_data"] = role_data

    # 3. Add provisional impact rating
    ratings = profile.get("card_impact_ratings", [])
    ratings.append({
        "card_name": card_name,
        "score": 5,
        "reason": "Provisional — regenerate strategy for full analysis",
    })
    profile["card_impact_ratings"] = ratings

    # 4. Mark as stale and track changes
    profile["simulation_stale"] = True
    profile["cards_changed_since_regen"] = profile.get("cards_changed_since_regen", 0) + 1

    deck.strategy_profile = profile


def _patch_strategy_card_removed(deck: Deck, card_name: str):
    """Incrementally update strategy profile when a card is removed.
    No AI calls — just data manipulation for instant updates."""
    profile = deck.strategy_profile
    if not profile:
        return

    # 1. Find and remove from role_data
    role_data = profile.get("role_data") or {}
    card_roles = role_data.get("card_roles", [])
    removed_role = None
    new_roles = []
    for cr in card_roles:
        if cr.get("card_name", "").lower() == card_name.lower():
            removed_role = cr.get("primary_role")
        else:
            new_roles.append(cr)
    role_data["card_roles"] = new_roles

    if removed_role:
        dist = role_data.get("role_distribution", {})
        if removed_role in dist:
            dist[removed_role] = max(0, dist[removed_role] - 1)
        role_data["role_distribution"] = dist
    profile["role_data"] = role_data

    # 2. Remove from impact ratings
    ratings = profile.get("card_impact_ratings", [])
    profile["card_impact_ratings"] = [
        r for r in ratings if r.get("card_name", "").lower() != card_name.lower()
    ]

    # 3. Remove from critical cards if present
    critical = profile.get("critical_cards", [])
    profile["critical_cards"] = [
        c for c in critical if c.lower() != card_name.lower()
    ]

    # 4. Mark as stale and track changes
    profile["simulation_stale"] = True
    profile["cards_changed_since_regen"] = profile.get("cards_changed_since_regen", 0) + 1

    deck.strategy_profile = profile


def _classify_single_card(type_line: str, oracle_text: str) -> str:
    """Quick rule-based role classification for a single card."""
    tl = type_line.lower()
    ot = (oracle_text or "").lower()

    if "land" in tl:
        return "land"
    if "add" in ot and ("{t}" in ot or "mana" in ot):
        return "ramp"
    if "search your library" in ot and "land" in ot:
        return "ramp"
    if "cost" in ot and "less" in ot:
        return "cost_reducer"
    if "draw" in ot and "card" in ot:
        return "card_draw"
    if "destroy" in ot or "exile" in ot:
        if "target" in ot:
            return "removal"
        if "all" in ot:
            return "board_wipe"
    if "counter target" in ot:
        return "removal"
    if "create" in ot and "token" in ot:
        return "token_generator"
    if "search your library" in ot:
        return "tutor"
    if "return" in ot and "graveyard" in ot:
        return "graveyard"
    if "hexproof" in ot or "indestructible" in ot or "protection" in ot:
        return "protection"
    if "creature" in tl:
        return "creature"
    return "utility"


# Basic lands exempt from singleton rule
BASIC_LANDS = {
    "plains", "island", "swamp", "mountain", "forest",
    "wastes", "snow-covered plains", "snow-covered island",
    "snow-covered swamp", "snow-covered mountain", "snow-covered forest",
}


# ─── Deck CRUD ─────────────────────────────────────────

@router.post("", response_model=DeckResponse, status_code=status.HTTP_201_CREATED)
def create_deck(
    request: DeckCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new deck for the authenticated user."""
    deck = Deck(
        user_id=user.id,
        name=request.name,
        format=request.format,
        description=request.description,
    )
    db.add(deck)
    db.commit()
    db.refresh(deck)
    return deck


@router.get("", response_model=list[DeckResponse])
def list_decks(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all decks belonging to the authenticated user."""
    return db.query(Deck).filter(Deck.user_id == user.id).order_by(Deck.updated_at.desc()).all()


@router.get("/{deck_id}", response_model=DeckDetailResponse)
def get_deck(
    deck_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a deck with all its cards."""
    deck = _get_user_deck(deck_id, user, db)
    return deck


@router.put("/{deck_id}", response_model=DeckResponse)
def update_deck(
    deck_id: UUID,
    request: DeckUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update deck name, format, or description."""
    deck = _get_user_deck(deck_id, user, db)

    if request.name is not None:
        deck.name = request.name
    if request.format is not None:
        deck.format = request.format
    if request.description is not None:
        deck.description = request.description

    db.commit()
    db.refresh(deck)
    return deck


@router.delete("/{deck_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_deck(
    deck_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a deck and all its cards."""
    deck = _get_user_deck(deck_id, user, db)
    db.delete(deck)
    db.commit()


# ─── Card Management ──────────────────────────────────

@router.post("/{deck_id}/cards", response_model=DeckCardResponse, status_code=status.HTTP_201_CREATED)
def add_card(
    deck_id: UUID,
    request: CardAdd,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Add a card to the deck.
    Enforces format rules:
    - Commander: singleton (max 1 copy except basic lands), max 100 cards, max 1 commander
    If the same card (same scryfall_id + board) already exists,
    the quantity is increased instead of creating a duplicate.
    """
    deck = _get_user_deck(deck_id, user, db)

    # Format validation for Commander
    if deck.format == "commander":
        current_cards = db.query(DeckCard).filter(DeckCard.deck_id == deck.id).all()
        total_count = sum(c.quantity for c in current_cards)

        # Max 100 cards (including commander)
        if total_count + request.quantity > 100:
            raise HTTPException(
                status_code=400,
                detail=f"Commander decks must have exactly 100 cards. Currently at {total_count}, cannot add {request.quantity} more.",
            )

        # Singleton rule (except basic lands)
        if request.card_name.lower() not in BASIC_LANDS:
            existing_any_board = db.query(DeckCard).filter(
                DeckCard.deck_id == deck.id,
                DeckCard.card_name == request.card_name,
            ).first()

            if existing_any_board:
                current_qty = existing_any_board.quantity
                if request.board == existing_any_board.board:
                    if current_qty + request.quantity > 1:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Commander is singleton format. {request.card_name} is already in the deck.",
                        )
                else:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Commander is singleton format. {request.card_name} is already in the deck on the {existing_any_board.board} board.",
                    )

            # Only 1 commander allowed (unless partner)
            if request.board == "commander":
                existing_commanders = db.query(DeckCard).filter(
                    DeckCard.deck_id == deck.id,
                    DeckCard.board == "commander",
                ).count()
                if existing_commanders >= 1:
                    raise HTTPException(
                        status_code=400,
                        detail="This deck already has a commander. Remove the current commander first.",
                    )

    # Check if card already in deck on the same board (by scryfall_id OR card_name)
    existing = db.query(DeckCard).filter(
        DeckCard.deck_id == deck.id,
        DeckCard.scryfall_id == request.scryfall_id,
        DeckCard.board == request.board,
    ).first()

    if not existing:
        # Also check by card name — different printings should stack
        existing = db.query(DeckCard).filter(
            DeckCard.deck_id == deck.id,
            DeckCard.card_name == request.card_name,
            DeckCard.board == request.board,
        ).first()

    if existing:
        existing.quantity += request.quantity
        db.commit()
        db.refresh(existing)
        return existing

    card = DeckCard(
        deck_id=deck.id,
        scryfall_id=request.scryfall_id,
        card_name=request.card_name,
        quantity=request.quantity,
        board=request.board,
    )
    db.add(card)
    _patch_strategy_card_added(deck, request.card_name, request.scryfall_id)
    if deck.strategy_profile is not None:
        flag_modified(deck, "strategy_profile")
    db.commit()
    # Log to deck intelligence (separate commit to not interfere with card add)
    try:
        log_card_added(deck, db, request.card_name, source="manual")
    except Exception:
        pass  # Intelligence logging is non-critical
    db.refresh(card)
    return card


@router.put("/{deck_id}/cards/{card_id}", response_model=DeckCardResponse)
def update_card(
    deck_id: UUID,
    card_id: UUID,
    request: CardUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a card's quantity or board (main/sideboard/commander)."""
    deck = _get_user_deck(deck_id, user, db)

    card = db.query(DeckCard).filter(
        DeckCard.id == card_id,
        DeckCard.deck_id == deck.id,
    ).first()

    if not card:
        raise HTTPException(status_code=404, detail="Card not found in this deck")

    if request.quantity is not None:
        # Check 100-card limit for Commander
        if deck.format == "commander" and request.quantity > card.quantity:
            current_cards = db.query(DeckCard).filter(DeckCard.deck_id == deck.id).all()
            total_count = sum(c.quantity for c in current_cards)
            added = request.quantity - card.quantity
            if total_count + added > 100:
                raise HTTPException(
                    status_code=400,
                    detail=f"Commander decks must have exactly 100 cards. Currently at {total_count}, cannot add {added} more.",
                )
        if request.quantity <= 0:
            removed_name = card.card_name
            db.delete(card)
            _patch_strategy_card_removed(deck, removed_name)
            if deck.strategy_profile is not None:
                flag_modified(deck, "strategy_profile")
            try:
                log_card_removed(deck, db, removed_name)
            except Exception:
                pass
            db.commit()
            return card  # Return the card before deletion — frontend will re-fetch anyway
        card.quantity = request.quantity

    if request.board is not None:
        card.board = request.board

    if request.notes is not None:
        card.notes = request.notes

    db.commit()
    db.refresh(card)
    return card

@router.put("/{deck_id}/cards/{card_id}/roles")
def update_card_roles(
    deck_id: UUID,
    card_id: UUID,
    roles: list[str],
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update user-assigned roles for a card."""
    deck = db.query(Deck).filter(Deck.id == deck_id).first()
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")
    if deck.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your deck")

    card = db.query(DeckCard).filter(
        DeckCard.id == card_id,
        DeckCard.deck_id == deck.id,
    ).first()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    ai_context = card.ai_context or {}
    ai_context["roles"] = roles
    card.ai_context = ai_context
    flag_modified(card, "ai_context")
    db.commit()

    return {"card_id": str(card.id), "roles": roles}

@router.put("/{deck_id}/preferences", response_model=DeckResponse)
def update_preferences(
    deck_id: UUID,
    request: DeckPreferences,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update deck preferences (user intent, constraints, play style).
    These preferences are injected into all AI prompts to ensure
    suggestions align with the user's vision for the deck.
    """
    deck = _get_user_deck(deck_id, user, db)

    # Merge with existing preferences (don't overwrite fields not provided)
    current = deck.preferences or {}
    update_data = request.model_dump(exclude_none=True)
    current.update(update_data)
    deck.preferences = current
    flag_modified(deck, "preferences")

    db.commit()
    db.refresh(deck)
    return deck


@router.delete("/{deck_id}/cards/{card_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_card(
    deck_id: UUID,
    card_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Remove a card from the deck entirely."""
    deck = _get_user_deck(deck_id, user, db)

    card = db.query(DeckCard).filter(
        DeckCard.id == card_id,
        DeckCard.deck_id == deck.id,
    ).first()

    if not card:
        raise HTTPException(status_code=404, detail="Card not found in this deck")

    card_name = card.card_name
    db.delete(card)
    _patch_strategy_card_removed(deck, card_name)
    if deck.strategy_profile is not None:
        flag_modified(deck, "strategy_profile")
    db.commit()
    try:
        log_card_removed(deck, db, card_name)
    except Exception:
        pass


@router.get("/{deck_id}/roles")
def get_deck_roles(
    deck_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all unique roles assigned to cards in this deck with counts."""
    deck = db.query(Deck).filter(Deck.id == deck_id).first()
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")
    if deck.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your deck")

    cards = db.query(DeckCard).filter(DeckCard.deck_id == deck.id).all()
    
    role_counts = {}
    role_cards = {}
    for card in cards:
        ai_context = card.ai_context or {}
        roles = ai_context.get("roles", [])
        for role in roles:
            role_counts[role] = role_counts.get(role, 0) + card.quantity
            if role not in role_cards:
                role_cards[role] = []
            role_cards[role].append(card.card_name)
    
    return {
        "roles": [
            {
                "role": role,
                "count": count,
                "cards": sorted(role_cards.get(role, [])),
            }
            for role, count in sorted(role_counts.items(), key=lambda x: -x[1])
        ]
    }


@router.post("/{deck_id}/roles/auto-suggest")
async def auto_suggest_roles(
    deck_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Auto-suggest roles for all cards based on oracle text analysis."""
    deck = db.query(Deck).filter(Deck.id == deck_id).first()
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")
    if deck.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your deck")

    from services.scryfall import scryfall_service

    cards = db.query(DeckCard).filter(DeckCard.deck_id == deck.id).all()
    
    # Only suggest for cards without existing roles
    untagged = [c for c in cards if not (c.ai_context or {}).get("roles")]
    if not untagged:
        return {"status": "all cards already tagged", "updated": 0}

    # Fetch card data from Scryfall in batches
    card_lookup = {}
    batch_size = 10
    for i in range(0, len(untagged), batch_size):
        batch = untagged[i:i + batch_size]
        identifiers = [{"id": c.scryfall_id} for c in batch]
        scryfall_data = await scryfall_service.get_collection(identifiers)
        for c in scryfall_data.get("data", []):
            card_lookup[c["id"]] = c

    updated = 0
    for card in untagged:
        card_data = card_lookup.get(card.scryfall_id)
        if not card_data:
            continue
        
        oracle = (card_data.get("oracle_text") or "").lower()
        # Handle double-faced cards
        if not oracle and card_data.get("card_faces"):
            face_texts = [f.get("oracle_text", "") for f in card_data["card_faces"]]
            oracle = " ".join(face_texts).lower()
        type_line = (card_data.get("type_line") or "")
        cmc = card_data.get("cmc", 0)
        suggested_roles = []

        # Skip basic lands only
        if "Basic" in type_line and "Land" in type_line:
            continue

        # Ramp detection
        if any(phrase in oracle for phrase in [
            "add {", "add one mana", "search your library for a basic land",
            "search your library for a land",
            "additional land", "mana of any", "mana of that color",
            "search your library for up to", "untap target land",
            "add an amount of {", "add mana",
            "untap target forest", "put a land",
            "search your library for a forest", "search your library for a basic",
        ]):
            # Exclude cards that give ramp to opponents
            if "opponent" not in oracle and "their library" not in oracle:
                if "Land" not in type_line:
                    suggested_roles.append("ramp")
        # Catch mana dorks
        if "creature" in type_line.lower() and ("add {" in oracle or "add one mana" in oracle):
            if "ramp" not in suggested_roles:
                suggested_roles.append("ramp")
        # Catch enchant land ramp
        if "enchant land" in oracle or ("enchant" in type_line.lower() and "add" in oracle and "mana" in oracle):
            if "ramp" not in suggested_roles:
                suggested_roles.append("ramp")

        # Artifact lands
        if "Artifact" in type_line and "Land" in type_line:
            suggested_roles.append("utility")

        # Cost reducers are ramp (but not self-discount like undaunted)
        if any(phrase in oracle for phrase in [
            "spells you cast cost", "cost less to cast",
            "reduce the cost",
        ]):
            # Exclude self-discount (undaunted, "this spell costs")
            if "this spell cost" not in oracle and "undaunted" not in oracle:
                if "ramp" not in suggested_roles:
                    suggested_roles.append("ramp")

        # Card draw
        if any(phrase in oracle for phrase in [
            "draw a card", "draw two", "draw three", "draw cards",
            "draw x card", "draws a card", "draw that many",
            "reveal the top", "put into your hand",
        ]):
            suggested_roles.append("card_draw")

        # Removal
        if any(phrase in oracle for phrase in [
            "destroy target", "exile target", "destroy another",
            "deals damage to any target", "deals damage to target",
            "-x/-x", "fight", "counter target spell",
            "destroy target artifact", "destroy target enchantment",
            "counter target noncreature", "counter target",
        ]):
            suggested_roles.append("removal")

        # Board wipe
        if any(phrase in oracle for phrase in [
            "destroy all", "exile all", "all creatures get -",
            "deals damage to each creature", "each creature gets -",
            "each player sacrifices", "destroy each",
            "deals 13 damage to each creature",
        ]):
            suggested_roles.append("board_wipe")

        # Protection
        if any(phrase in oracle for phrase in [
            "hexproof", "indestructible", "shroud", "protection from",
            "can't be countered", "can't be destroyed", "prevent all damage",
            "fog", "prevent the next", "prevent all combat damage",
            "regenerate target", "regenerate",
        ]):
            suggested_roles.append("protection")

        # Tutor (non-land search)
        if "search your library" in oracle and not any(lt in oracle for lt in [
            "land", "forest", "island", "mountain", "swamp", "plains",
        ]):
            suggested_roles.append("tutor")

        # Recursion
        if any(phrase in oracle for phrase in [
            "return target", "return a", "from your graveyard to your hand",
            "from your graveyard to the battlefield", "cast from your graveyard",
            "return it to", "from a graveyard",
        ]):
            suggested_roles.append("recursion")

        # Combo enablers
        if any(phrase in oracle for phrase in [
            "untap all", "untap each", "untap target artifact",
            "untap target permanent", "storm",
            "whenever you cast", "whenever a player casts",
            "copy that spell", "cast it without paying",
        ]):
            suggested_roles.append("combo")

        # Tokens
        if "create" in oracle and "token" in oracle:
            suggested_roles.append("tokens")

        # # Finisher — creatures with big power or pump effects
        if any(phrase in oracle for phrase in [
            "each opponent", "deals x damage", "lose life equal",
            "gain control", "extra turn", "trample",
            "get +", "gets +", "double the power", "double target",
            "power and toughness each equal", "double target creature",
            "all creatures you control get", "creatures you control get +", "double target creature", "doubles",
        ]):
            suggested_roles.append("finisher")

        # Overrun effects
        if any(phrase in oracle for phrase in [
            "creatures you control get +", "all creatures you control",
            "each creature you control gets",
        ]):
            if "finisher" not in suggested_roles:
                suggested_roles.append("finisher")

        # Catch big creatures as finishers
        power = card_data.get("power")
        if power and power.isdigit() and int(power) >= 6:
            if "finisher" not in suggested_roles:
                suggested_roles.append("finisher")

        # Utility — catch-all for unclassified nonland cards
        if not suggested_roles:
            if "Land" not in type_line or "//" in type_line:
                suggested_roles.append("utility")

        if suggested_roles:
            ai_context = card.ai_context or {}
            ai_context["roles"] = suggested_roles
            card.ai_context = ai_context
            flag_modified(card, "ai_context")
            updated += 1

    db.commit()

    return {"status": "ok", "updated": updated, "skipped_tagged": len(cards) - len(untagged)}