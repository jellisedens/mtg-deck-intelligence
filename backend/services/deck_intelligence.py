"""
Deck Intelligence Service

Manages the per-deck intelligence layer — the accumulated understanding
of what a deck does, what the user wants, and what has happened over time.

This is separate from the strategy profile (which is regenerated) —
the intelligence persists and grows across sessions.
"""

from datetime import datetime, timezone
from sqlalchemy.orm.attributes import flag_modified


# Default structure for a new deck intelligence
def _default_intelligence() -> dict:
    return {
        "understanding": {
            "game_plan": None,
            "win_conditions": [],
            "key_synergies": [],
            "known_weaknesses": [],
            "backup_plans": [],
        },
        "history": {
            "suggestion_log": [],
            "card_changes": [],
            "insight_updates": [],
        },
        "preferences": {
            "budget_sensitivity": None,
            "power_level": None,
            "card_style": None,
            "meta_notes": [],
            "combo_tolerance": None,
        },
        "accumulated_insight": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }


def get_or_create_intelligence(deck) -> dict:
    """Get the deck's intelligence, creating the default structure if it doesn't exist."""
    if deck.deck_intelligence is None:
        deck.deck_intelligence = _default_intelligence()
    return deck.deck_intelligence


def log_suggestion(deck, db_session, prompt: str, suggestions: list,
                   intent: str = "suggest") -> None:
    """Log a suggestion interaction to the deck's intelligence history."""
    intel = get_or_create_intelligence(deck)
    
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "intent": intent,
        "prompt": prompt,
        "suggestions_offered": [s.get("card_name", "") for s in suggestions],
        "cards_accepted": [],  # filled in when user clicks "add"
        "cards_rejected": [],  # filled in later by comparison
    }
    
    intel["history"]["suggestion_log"].append(entry)
    
    # Keep only last 50 suggestion logs
    if len(intel["history"]["suggestion_log"]) > 50:
        intel["history"]["suggestion_log"] = intel["history"]["suggestion_log"][-50:]
    
    intel["last_updated"] = datetime.now(timezone.utc).isoformat()
    deck.deck_intelligence = intel
    flag_modified(deck, "deck_intelligence")
    db_session.add(deck)
    db_session.commit()


def log_card_added(deck, db_session, card_name: str, source: str = "manual") -> None:
    """Log a card addition to the deck's intelligence history."""
    intel = get_or_create_intelligence(deck)
    
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": "added",
        "card_name": card_name,
        "source": source,  # "manual", "ai_suggestion", "import"
    }
    
    intel["history"]["card_changes"].append(entry)
    
    # If this card was in the most recent suggestion log, mark it as accepted
    suggestion_log = intel["history"]["suggestion_log"]
    if suggestion_log:
        latest = suggestion_log[-1]
        if card_name in latest.get("suggestions_offered", []):
            if card_name not in latest.get("cards_accepted", []):
                latest["cards_accepted"].append(card_name)
    
    # Keep only last 100 card changes
    if len(intel["history"]["card_changes"]) > 100:
        intel["history"]["card_changes"] = intel["history"]["card_changes"][-100:]
    
    intel["last_updated"] = datetime.now(timezone.utc).isoformat()
    deck.deck_intelligence = intel
    flag_modified(deck, "deck_intelligence")
    db_session.add(deck)
    db_session.commit()


def log_card_removed(deck, db_session, card_name: str) -> None:
    """Log a card removal to the deck's intelligence history."""
    intel = get_or_create_intelligence(deck)
    
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": "removed",
        "card_name": card_name,
    }
    
    intel["history"]["card_changes"].append(entry)
    
    # Keep only last 100 card changes
    if len(intel["history"]["card_changes"]) > 100:
        intel["history"]["card_changes"] = intel["history"]["card_changes"][-100:]
    
    intel["last_updated"] = datetime.now(timezone.utc).isoformat()
    deck.deck_intelligence = intel
    flag_modified(deck, "deck_intelligence")
    db_session.add(deck)
    db_session.commit()


def seed_from_strategy_profile(deck, db_session) -> None:
    """
    Populate the understanding section from the strategy profile.
    Called after strategy generation to sync the intelligence with the profile.
    """
    profile = deck.strategy_profile
    if not profile:
        return
    
    intel = get_or_create_intelligence(deck)
    
    intel["understanding"]["game_plan"] = profile.get("primary_strategy")
    intel["understanding"]["win_conditions"] = profile.get("win_conditions", [])
    intel["understanding"]["known_weaknesses"] = profile.get("weaknesses", [])
    
    # Extract synergy descriptions
    synergies = []
    for syn in profile.get("key_synergies", []):
        cards = syn.get("cards", [])
        desc = syn.get("description", "")
        synergies.append(f"{' + '.join(cards)}: {desc}")
    intel["understanding"]["key_synergies"] = synergies
    
    intel["history"]["insight_updates"].append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "strategy_generation",
        "message": "Intelligence seeded from strategy profile generation",
    })
    
    intel["last_updated"] = datetime.now(timezone.utc).isoformat()
    deck.deck_intelligence = intel
    flag_modified(deck, "deck_intelligence")
    db_session.add(deck)
    db_session.commit()


def get_intelligence_context(deck) -> str:
    """
    Build a compact context string from the deck intelligence
    for injection into AI prompts.
    """
    intel = deck.deck_intelligence
    if not intel:
        return ""
    
    parts = []
    
    # Understanding
    understanding = intel.get("understanding", {})
    if understanding.get("game_plan"):
        parts.append(f"Deck plan: {understanding['game_plan']}")
    if understanding.get("known_weaknesses"):
        parts.append(f"Known weaknesses: {', '.join(understanding['known_weaknesses'][:3])}")
    
    # Preferences
    prefs = intel.get("preferences", {})
    if prefs.get("power_level"):
        parts.append(f"Power level: {prefs['power_level']}")
    if prefs.get("budget_sensitivity"):
        parts.append(f"Budget: {prefs['budget_sensitivity']}")
    if prefs.get("meta_notes"):
        parts.append(f"Meta notes: {'; '.join(prefs['meta_notes'][:3])}")
    
    # Recent history summary
    history = intel.get("history", {})
    recent_changes = history.get("card_changes", [])[-5:]
    if recent_changes:
        change_summary = []
        for ch in recent_changes:
            action = ch.get("action", "?")
            card = ch.get("card_name", "?")
            change_summary.append(f"{action}: {card}")
        parts.append(f"Recent changes: {', '.join(change_summary)}")
    
    # Accumulated insights
    insights = intel.get("accumulated_insight", [])
    if insights:
        parts.append(f"AI insights: {'; '.join(insights[:3])}")
    
    return "\n".join(parts)