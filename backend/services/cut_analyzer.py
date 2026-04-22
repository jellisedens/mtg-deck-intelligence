"""
Cut candidate analyzer.
Evaluates which cards can be safely cut from a deck based on
impact ratings, simulation data, and role distribution.
"""

import json


def build_cut_context(deck_info: dict, simulation_data: dict = None,
                      deck_cards: list = None, card_lookup: dict = None) -> str:
    """
    Build a formatted string of cut candidates for the AI prompt.
    Uses impact ratings from the strategy profile, filtered by
    simulation performance data.
    """
    profile = deck_info.get("strategy_profile") or {}
    impact_ratings = profile.get("card_impact_ratings", [])

    if not impact_ratings:
        return "\nNo card impact ratings available. Use role distribution and deck context to identify the weakest cards."

    # Build land name set
    land_names = set()
    if deck_cards and card_lookup:
        for dc in deck_cards:
            card_data = card_lookup.get(dc.scryfall_id, {})
            if "Land" in card_data.get("type_line", ""):
                land_names.add(dc.card_name.lower())

    # Split ratings into non-land and land candidates
    non_land_ratings = [
        r for r in impact_ratings
        if r.get("score", 10) <= 8
        and r.get("card_name", "").lower() not in land_names
    ]
    land_ratings = [
        r for r in impact_ratings
        if r.get("score", 10) <= 6
        and r.get("card_name", "").lower() in land_names
    ]

    non_land_ratings.sort(key=lambda r: r.get("score", 5))
    land_ratings.sort(key=lambda r: r.get("score", 5))

    lines = []

    # Non-land cut candidates (bottom 10)
    bottom_10 = non_land_ratings[:10]
    if bottom_10:
        lines.append("\n=== CUT CANDIDATES (ranked by impact score, weakest first) ===")
        lines.append("These are the lowest-impact cards in the deck. Pick 2-3 from this list:")
        for rank, r in enumerate(bottom_10, 1):
            lines.append(f"{rank}. {r['card_name']} (impact: {r['score']}/10) — {r.get('reason', '')}")

    protected_count = len([r for r in impact_ratings if r.get("score", 0) >= 9])
    strong_count = len([r for r in impact_ratings if 7 <= r.get("score", 0) <= 8])
    lines.append(f"\nDeck health: {protected_count} core cards (9-10), {strong_count} strong cards (7-8).")
    lines.append("If all candidates score 5+, the deck is well-optimized. Still suggest 2-3 of the LOWEST scoring cards but note the tradeoff.")
    lines.append("=== END CUT CANDIDATES ===")

    # Land swap candidates
    land_context = _build_land_swap_context(land_ratings, simulation_data)
    if land_context:
        lines.append(land_context)

    return "\n".join(lines)


def _build_land_swap_context(land_ratings: list, simulation_data: dict = None) -> str:
    """Build land swap suggestions based on simulation performance."""
    if not land_ratings:
        return ""

    if not simulation_data or "per_turn_averages" not in simulation_data:
        return ""

    turns = simulation_data.get("per_turn_averages", [])
    turn3 = turns[2] if len(turns) > 2 else {}
    turn5 = turns[4] if len(turns) > 4 else {}

    mana_on_curve_t3 = turn3.get("mana_on_curve_rate", 0)
    mana_healthy = mana_on_curve_t3 >= 85

    lines = []

    if mana_healthy:
        lines.append("\n=== LAND SWAP CANDIDATES ===")
        lines.append(f"Mana development is healthy ({mana_on_curve_t3}% on curve by turn 3).")
        lines.append("These lands could be SWAPPED for better options (do NOT reduce total land count):")
        for r in land_ratings[:5]:
            lines.append(f"- {r['card_name']} (impact: {r['score']}/10) — {r.get('reason', '')}")

        color_access = turn5.get("color_access_rates", {})
        weak_colors = [c for c, pct in color_access.items() if pct < 75]
        if weak_colors:
            lines.append(f"WARNING: Colors {', '.join(weak_colors)} have weak access by turn 5. Do NOT cut lands that produce these colors.")

        lines.append("IMPORTANT: If suggesting a land cut, ALSO suggest a replacement land. Frame as a swap, not a pure cut.")
        lines.append("=== END LAND SWAPS ===")
    else:
        lines.append(f"\nNOTE: Mana development is below average ({mana_on_curve_t3}% on curve by turn 3). Do NOT suggest cutting any lands.")

    return "\n".join(lines)


def get_impact_summary(deck_info: dict) -> dict:
    """Return a summary of impact rating distribution for debugging/frontend."""
    profile = deck_info.get("strategy_profile") or {}
    impact_ratings = profile.get("card_impact_ratings", [])

    if not impact_ratings:
        return {"available": False}

    scores = [r.get("score", 5) for r in impact_ratings]

    return {
        "available": True,
        "total_rated": len(scores),
        "average_score": round(sum(scores) / len(scores), 1),
        "distribution": {
            "core_9_10": len([s for s in scores if s >= 9]),
            "strong_7_8": len([s for s in scores if 7 <= s <= 8]),
            "solid_5_6": len([s for s in scores if 5 <= s <= 6]),
            "flexible_3_4": len([s for s in scores if 3 <= s <= 4]),
            "cuttable_1_2": len([s for s in scores if s <= 2]),
        },
    }