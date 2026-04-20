"""
AI-powered simulation results analyzer.
Takes raw simulation data and generates plain-English insights.
"""

import os
import json
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL = "gpt-4o-mini"


def analyze_simulation(simulation_data: dict, deck_info: dict = None,
                       strategy_profile: dict = None) -> dict:
    """
    Generate a plain-English analysis of simulation results.
    """
    system = """You are an expert Magic: The Gathering deck analyst reviewing goldfish simulation results.
Explain the data in clear, actionable language that helps players understand their deck's performance.

Respond with ONLY valid JSON (no markdown, no backticks):
{
    "overall_grade": "A/B/C/D/F",
    "summary": "2-3 sentence overview of deck performance",
    "mana_development": {
        "assessment": "strong/adequate/weak",
        "details": "Analysis of land drops, mana curve, and ramp effectiveness"
    },
    "color_fixing": {
        "assessment": "strong/adequate/weak",
        "details": "Analysis of color access over time, when all colors become available"
    },
    "board_development": {
        "assessment": "strong/adequate/weak",
        "details": "Analysis of creature deployment and power on board"
    },
    "card_flow": {
        "assessment": "strong/adequate/weak",
        "details": "Analysis of cards in hand, draw rate, running out of gas"
    },
    "castability": {
        "assessment": "strong/adequate/weak",
        "details": "Analysis of how often spells are castable vs stuck in hand"
    },
    "key_turns": [
        {"turn": 3, "insight": "What happens at this critical turn"},
        {"turn": 5, "insight": "What happens at this critical turn"}
    ],
    "recommendations": [
        "Specific actionable improvement suggestion based on the data"
    ],
    "benchmarks": {
        "lands_on_curve": "Are you hitting land drops consistently?",
        "ramp_effectiveness": "How much does ramp accelerate your mana?",
        "threat_deployment": "When do threats start hitting the board?"
    }
}"""

    user_msg = "Simulation results:\n"
    user_msg += json.dumps(simulation_data, indent=2)

    if deck_info:
        user_msg += f"\n\nDeck: {deck_info.get('name', 'Unknown')}"
        user_msg += f"\nFormat: {deck_info.get('format', 'Unknown')}"
        user_msg += f"\nDescription: {deck_info.get('description', '')}"

    if strategy_profile:
        user_msg += f"\n\nStrategy profile:\n"
        user_msg += f"Commander role: {strategy_profile.get('commander_role', 'Unknown')}\n"
        user_msg += f"Primary strategy: {strategy_profile.get('primary_strategy', 'Unknown')}\n"
        user_msg += f"Win conditions: {json.dumps(strategy_profile.get('win_conditions', []))}\n"
        user_msg += f"Weaknesses: {json.dumps(strategy_profile.get('weaknesses', []))}\n"

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.3,
        )

        content = response.choices[0].message.content.strip()
        content = content.replace("```json", "").replace("```", "").strip()
        return json.loads(content)

    except Exception as e:
        return {"error": str(e)}