"""
Mana health analyzer.
Computes per-color health scores combining simulation performance
with static deck composition analysis.
"""


def compute_color_health(simulation_data: dict, analytics: dict) -> dict:
    """
    Compute a single health score (0-100) per color combining:
    - Simulation access rate (70% weight) - actual measured performance
    - Source adequacy (30% weight) - structural capacity (sources vs pips needed)

    Higher score = healthier. Lower score = needs fixing first.
    """
    if not simulation_data or "per_turn_averages" not in simulation_data:
        return _static_only_health(analytics)

    turns = simulation_data.get("per_turn_averages", [])
    turn5 = turns[4] if len(turns) > 4 else {}
    color_access = turn5.get("color_access_rates", {})

    colors = analytics.get("color_distribution", {})
    color_pips = {c: info.get("count", 0) for c, info in colors.items() if info.get("count", 0) > 0}
    mana_base = analytics.get("mana_base", {})
    color_sources = mana_base.get("color_sources", {})

    color_health = {}
    for color in ["W", "U", "B", "R", "G"]:
        pips = color_pips.get(color, 0)
        sources = color_sources.get(color, 0)
        sim_access = color_access.get(color, 0)

        if pips > 0:
            adequacy = min(100, (sources / pips) * 100)
        elif sources > 0:
            adequacy = 100
        else:
            adequacy = 0

        health = (sim_access * 0.7) + (adequacy * 0.3)

        color_health[color] = {
            "score": round(health, 1),
            "sim_access": sim_access,
            "sources": sources,
            "pips": pips,
            "adequacy": round(adequacy, 1),
        }

    fix_priority = sorted(color_health.keys(), key=lambda c: color_health[c]["score"])
    scores = [color_health[c]["score"] for c in color_health]
    overall = round(sum(scores) / len(scores), 1) if scores else 0

    critical = [c for c in fix_priority if color_health[c]["score"] < 65]
    healthy = [c for c in fix_priority if color_health[c]["score"] >= 80]

    return {
        "color_health": color_health,
        "fix_priority": fix_priority,
        "overall_health": overall,
        "critical_colors": critical,
        "healthy_colors": healthy,
    }


def _static_only_health(analytics: dict) -> dict:
    """Fallback when no simulation data is available."""
    colors = analytics.get("color_distribution", {})
    color_pips = {c: info.get("count", 0) for c, info in colors.items() if info.get("count", 0) > 0}
    mana_base = analytics.get("mana_base", {})
    color_sources = mana_base.get("color_sources", {})

    color_health = {}
    for color in ["W", "U", "B", "R", "G"]:
        pips = color_pips.get(color, 0)
        sources = color_sources.get(color, 0)

        if pips > 0:
            adequacy = min(100, (sources / pips) * 100)
        elif sources > 0:
            adequacy = 100
        else:
            adequacy = 0

        color_health[color] = {
            "score": round(adequacy, 1),
            "sim_access": None,
            "sources": sources,
            "pips": pips,
            "adequacy": round(adequacy, 1),
        }

    fix_priority = sorted(color_health.keys(), key=lambda c: color_health[c]["score"])
    scores = [color_health[c]["score"] for c in color_health]
    overall = round(sum(scores) / len(scores), 1) if scores else 0

    return {
        "color_health": color_health,
        "fix_priority": fix_priority,
        "overall_health": overall,
        "critical_colors": [c for c in fix_priority if color_health[c]["score"] < 65],
        "healthy_colors": [c for c in fix_priority if color_health[c]["score"] >= 80],
    }


def format_color_health_for_prompt(health_data: dict) -> str:
    """Format color health data as a compact string for AI prompts."""
    if not health_data or not health_data.get("color_health"):
        return ""

    color_health = health_data["color_health"]
    fix_priority = health_data.get("fix_priority", [])
    overall = health_data.get("overall_health", 0)
    critical = health_data.get("critical_colors", [])

    lines = [f"Mana Health (0-100, lower=worse): overall {overall}"]

    parts = []
    for color in fix_priority:
        ch = color_health[color]
        marker = " CRITICAL" if color in critical else ""
        parts.append(f"{color}: {ch['score']} ({ch['sources']} sources / {ch['pips']} pips, {ch['sim_access']}% sim access){marker}")

    lines.append("  " + " | ".join(parts))

    if critical:
        lines.append(f"FIX FIRST: {', '.join(critical)} (score below 65)")

    return "\n".join(lines)