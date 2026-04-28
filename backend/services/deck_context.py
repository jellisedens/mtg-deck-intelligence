"""
Deck context builder.
Prepares structured text summaries of deck state for AI prompts.
Reusable across suggestion, simulation analysis, and other AI features.
"""

import json


def build_deck_context(deck_cards: list, deck_info: dict, analytics: dict,
                       card_lookup: dict = None, role_data: dict = None) -> str:
    """Build a rich text summary of the deck for AI prompts."""
    lines = []

    if deck_info:
        lines.append(f"Deck: {deck_info.get('name', 'Unknown')}")
        lines.append(f"Format: {deck_info.get('format', 'Unknown')}")
        if deck_info.get("description"):
            lines.append(f"Strategy: {deck_info['description']}")
        if deck_info.get("strategy_profile"):
            profile = deck_info["strategy_profile"]
            lines.append(f"\n=== STRATEGIC PROFILE ===")
            lines.append(f"Commander role: {profile.get('commander_role', 'Unknown')}")
            lines.append(f"Primary strategy: {profile.get('primary_strategy', 'Unknown')}")
            lines.append(f"Win conditions: {json.dumps(profile.get('win_conditions', []))}")
            key_synergies = profile.get("key_synergies", [])
            if key_synergies:
                lines.append("Key synergies:")
                for syn in key_synergies[:5]:
                    lines.append(f"  - {' + '.join(syn.get('cards', []))}: {syn.get('description', '')}")
            lines.append(f"Critical cards (never cut): {json.dumps(profile.get('critical_cards', []))}")
            lines.append(f"Weaknesses: {json.dumps(profile.get('weaknesses', []))}")
            role_needs = profile.get("role_needs", {})
            if role_needs.get("needs_more"):
                lines.append(f"Needs more: {json.dumps(role_needs['needs_more'])}")
            if role_needs.get("over_saturated"):
                lines.append(f"Over-saturated: {json.dumps(role_needs['over_saturated'])}")
            lines.append(f"Cut guidance: {profile.get('cut_guidance', 'None')}")
            lines.append(f"=== END STRATEGIC PROFILE ===\n")

    lines.append(f"\nTotal cards: {analytics.get('total_cards', 0)}")
    lines.append(f"Average CMC: {analytics.get('average_cmc', 0)}")

    if role_data:
        lines.append(f"\nPrimary creature type: {role_data.get('primary_creature_type', 'None')}")
        lines.append("\nStrategic role distribution:")
        role_dist = role_data.get("role_distribution", {})
        for role, count in sorted(role_dist.items(), key=lambda x: -x[1]):
            if count > 0:
                lines.append(f"  {role}: {count}")

    lines.append("\nCurrent deck list:")
    role_lookup = {}
    if role_data:
        for cr in role_data.get("card_roles", []):
            role_lookup[cr["name"].lower()] = cr

    for card in deck_cards:
        role_info = role_lookup.get(card.card_name.lower(), {})
        primary_role = role_info.get("primary_role", "unknown")
        secondary = role_info.get("secondary_roles", [])
        synergy = role_info.get("synergy_notes", "")

        oracle_text = ""
        if card_lookup:
            full_data = card_lookup.get(card.scryfall_id, {})
            oracle_text = full_data.get("oracle_text", "")

        role_str = f"[{primary_role}]"
        if secondary:
            role_str += f" (also: {', '.join(secondary)})"

        lines.append(f"  {card.quantity}x {card.card_name} ({card.board}) {role_str}")
        if oracle_text:
            lines.append(f"     Text: {oracle_text[:120]}")
        if hasattr(card, 'notes') and card.notes:
            lines.append(f"     User notes: {card.notes}")
        if hasattr(card, 'ai_context') and card.ai_context:
            ai_ctx = card.ai_context
            if ai_ctx.get('impact_score'):
                lines.append(f"     Impact: {ai_ctx['impact_score']}/10 - {ai_ctx.get('impact_reason', '')}")

    identity = analytics.get("deck_identity", {})
    if identity:
        lines.append(f"\nDeck identity: {identity.get('recommendation_weight', 'balanced')}")
        lines.append(f"Non-land breakdown: {json.dumps(identity.get('type_percentages', {}))}")
        lines.append(f"Spells (instant+sorcery): {identity.get('spell_count', 0)} | Permanents (creature+enchantment+artifact+planeswalker): {identity.get('permanent_count', 0)} ({identity.get('spell_vs_permanent', 'balanced')})")
        lines.append(f"IMPORTANT: This deck is {identity.get('recommendation_weight', 'balanced')} — all suggestions for ramp, draw, removal, and utility should align with this identity")

    curve = analytics.get("mana_curve", {})
    lines.append(f"\nMana curve: {json.dumps(curve)}")

    colors = analytics.get("color_distribution", {})
    color_summary = {c: info["count"] for c, info in colors.items() if info["count"] > 0}
    lines.append(f"Color symbols in mana costs: {json.dumps(color_summary)}")

    types = analytics.get("type_distribution", {})
    type_summary = {t: c for t, c in types.items() if c > 0}
    lines.append(f"Card types: {json.dumps(type_summary)}")

    mana_base = analytics.get("mana_base", {})
    lines.append(f"Lands: {mana_base.get('land_count', 0)} ({mana_base.get('land_percentage', 0)}%)")
    lines.append(f"Color sources: {json.dumps(mana_base.get('color_sources', {}))}")

    return "\n".join(lines)


def build_simulation_context(simulation_data: dict) -> str:
    """
    Extract decision-relevant statistics from simulation results
    and format them for AI prompts.
    """
    if not simulation_data or "per_turn_averages" not in simulation_data:
        return ""

    turns = simulation_data["per_turn_averages"]
    n_games = simulation_data.get("games_simulated", 0)

    lines = [
        f"\n=== SIMULATION PERFORMANCE DATA ({n_games} games simulated) ===",
    ]

    milestone_turns = [1, 3, 5, 7]
    for t_num in milestone_turns:
        t_idx = t_num - 1
        if t_idx >= len(turns):
            continue
        t = turns[t_idx]

        lines.append(f"\nTurn {t_num}:")
        lines.append(f"  Lands on board: {t.get('avg_lands_on_board', 0)}")
        lines.append(f"  Total mana available: {t.get('avg_total_mana_available', 0)}")
        lines.append(f"  Mana on curve rate: {t.get('mana_on_curve_rate', 0)}%")
        lines.append(f"  On curve (cast a spell): {t.get('on_curve_rate', 0)}%")
        lines.append(f"  Castable cards after land drop: {t.get('avg_castable_after_land', 0)}")
        lines.append(f"  Uncastable cards in hand: {t.get('avg_uncastable_cards', 0)}")
        lines.append(f"  Creatures on board: {t.get('avg_creatures_on_board', 0)}")
        lines.append(f"  Total power on board: {t.get('avg_total_power_on_board', 0)}")

        access = t.get("color_access_rates", {})
        if access:
            weak_colors = [f"{c}: {pct}%" for c, pct in access.items() if pct < 80]
            strong_colors = [f"{c}: {pct}%" for c, pct in access.items() if pct >= 80]
            if weak_colors:
                lines.append(f"  WEAK color access: {', '.join(weak_colors)}")
            if strong_colors:
                lines.append(f"  Strong color access: {', '.join(strong_colors)}")

        lines.append(f"  All 5 colors available: {t.get('all_colors_rate', 0)}%")

    lines.append("\n--- PERFORMANCE DIAGNOSIS ---")

    turn3 = turns[2] if len(turns) > 2 else {}
    turn5 = turns[4] if len(turns) > 4 else {}

    mana_t3 = turn3.get("mana_on_curve_rate", 0)

    if mana_t3 < 70:
        lines.append(f"WARNING: Mana development is POOR — only {mana_t3}% on curve by turn 3. Deck needs more ramp or lands.")
    elif mana_t3 < 85:
        lines.append(f"CAUTION: Mana development is below average — {mana_t3}% on curve by turn 3.")
    else:
        lines.append(f"Mana development is healthy — {mana_t3}% on curve by turn 3.")

    uncastable_t5 = turn5.get("avg_uncastable_cards", 0)
    if uncastable_t5 > 3:
        lines.append(f"WARNING: High card stuck rate — {uncastable_t5} uncastable cards in hand by turn 5. Curve may be too high or color fixing insufficient.")
    elif uncastable_t5 > 2:
        lines.append(f"CAUTION: {uncastable_t5} uncastable cards by turn 5 — consider lowering curve or adding fixing.")

    # Sort colors by access rate (worst first) for prioritized fixing
    turn5_access = turn5.get("color_access_rates", {})
    sorted_access = sorted(turn5_access.items(), key=lambda x: x[1])
    for color, pct in sorted_access:
        if pct < 60:
            lines.append(f"CRITICAL: {color} access is only {pct}% by turn 5 — HIGHEST PRIORITY for fixing.")
        elif pct < 75:
            lines.append(f"WARNING: {color} access is weak at {pct}% by turn 5 — add more {color}-producing lands or rocks.")
    
    if sorted_access:
        worst_color, worst_pct = sorted_access[0]
        lines.append(f"WORST color access: {worst_color} at {worst_pct}% — fix this color FIRST.")

    power_t5 = turn5.get("avg_total_power_on_board", 0)
    creatures_t5 = turn5.get("avg_creatures_on_board", 0)
    if creatures_t5 < 1:
        lines.append(f"WARNING: Only {creatures_t5} creatures on board by turn 5 — threats deploy too slowly.")
    if power_t5 < 5:
        lines.append(f"WARNING: Only {power_t5} total power by turn 5 — board presence is weak.")

    all_colors_t5 = turn5.get("all_colors_rate", 0)
    if all_colors_t5 < 50:
        lines.append(f"WARNING: All 5 colors available only {all_colors_t5}% of the time by turn 5. Mana base needs better fixing.")

    lines.append("=== END SIMULATION DATA ===\n")

    return "\n".join(lines)