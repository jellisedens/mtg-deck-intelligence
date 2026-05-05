"""
Lightweight strategy profile updates after card changes.
No AI calls — just data manipulation for instant updates.
Full regeneration happens when user explicitly requests it.
"""

from services.scryfall import scryfall_service


def patch_card_added(deck, card_scryfall_data: dict, db_session):
    """Update strategy profile incrementally after a card is added."""
    profile = deck.strategy_profile
    if not profile:
        return  # No profile to patch — user hasn't generated one yet
    
    card_name = card_scryfall_data.get("name", "")
    type_line = card_scryfall_data.get("type_line", "")
    oracle_text = card_scryfall_data.get("oracle_text", "")
    mana_cost = card_scryfall_data.get("mana_cost", "")
    colors = card_scryfall_data.get("color_identity", [])
    
    # 1. Classify role for this single card (rule-based, no AI)
    role = _classify_single_card(type_line, oracle_text, mana_cost)
    
    # 2. Update role_data
    role_data = profile.get("role_data") or {}
    card_roles = role_data.get("card_roles", [])
    card_roles.append({
        "card_name": card_name,
        "primary_role": role,
        "secondary_roles": [],
    })
    role_data["card_roles"] = card_roles
    
    # Update distribution
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
    
    # 4. Update color health (simple recalc)
    _update_color_counts(profile, mana_cost, colors, add=True)
    
    # 5. Mark simulation as stale
    profile["simulation_stale"] = True
    
    # 6. Save
    deck.strategy_profile = profile
    db_session.add(deck)
    db_session.commit()


def patch_card_removed(deck, card_name: str, db_session):
    """Update strategy profile incrementally after a card is removed."""
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
    
    # Update distribution
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
    
    # 4. Mark simulation as stale
    profile["simulation_stale"] = True
    
    # 5. Save
    deck.strategy_profile = profile
    db_session.add(deck)
    db_session.commit()


def _classify_single_card(type_line: str, oracle_text: str, mana_cost: str) -> str:
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


def _update_color_counts(profile: dict, mana_cost: str, color_identity: list, add: bool):
    """Lightweight color health update — just adjust source counts."""
    color_health = profile.get("color_health")
    if not color_health or not isinstance(color_health, list):
        return
    
    # Check if this card produces colored mana (lands, dorks, rocks)
    # This is approximate — full recalc happens on regeneration
    for ch in color_health:
        color = ch.get("color", "")
        if color in color_identity:
            if add:
                ch["sources"] = ch.get("sources", 0) + 1
            else:
                ch["sources"] = max(0, ch.get("sources", 0) - 1)
    
    profile["color_health"] = color_health