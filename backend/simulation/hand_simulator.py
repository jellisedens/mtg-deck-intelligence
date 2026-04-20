"""
Opening hand Monte Carlo simulator.
Shuffles the deck and draws opening hands N times,
computing probabilities for lands, playable cards, and specific card types.
"""

import random
from collections import defaultdict


def simulate_opening_hands(cards: list, n_simulations: int = 1000,
                           mulligan_to: int = 7) -> dict:
    """
    Run N simulations of drawing opening hands.

    Args:
        cards: list of dicts, each with card_data (from Scryfall) and quantity
        n_simulations: number of hands to simulate
        mulligan_to: hand size (7 = no mulligan, 6 = one mulligan, etc.)

    Returns:
        dict with probability tables and sample hands
    """
    if not cards:
        return {"error": "No cards to simulate"}

    # Build the virtual deck as a flat list (respecting quantities)
    deck = []
    for card_entry in cards:
        card_data = card_entry["card_data"]
        quantity = card_entry.get("quantity", 1)
        for _ in range(quantity):
            deck.append(card_data)

    if len(deck) < 7:
        return {"error": f"Deck has only {len(deck)} cards — need at least 7"}

    # Tracking counters
    land_counts = defaultdict(int)
    cmc_slot_hits = defaultdict(int)
    type_hits = defaultdict(int)
    color_in_hand = defaultdict(int)
    playable_turn_1 = 0
    playable_turn_2 = 0
    keepable_hands = 0
    sample_hands = []

    for i in range(n_simulations):
        # Shuffle and draw
        shuffled = deck.copy()
        random.shuffle(shuffled)
        hand = shuffled[:mulligan_to]

        # Analyze the hand
        lands_in_hand = []
        spells_in_hand = []

        for card in hand:
            type_line = card.get("type_line", "")
            if "Land" in type_line:
                lands_in_hand.append(card)
            else:
                spells_in_hand.append(card)

        num_lands = len(lands_in_hand)
        land_counts[num_lands] += 1

        # Keepable = 2-4 lands in hand
        if 2 <= num_lands <= 4:
            keepable_hands += 1

        # CMC slot hits
        for spell in spells_in_hand:
            cmc = int(spell.get("cmc", 0))
            cmc_key = min(cmc, 7)
            cmc_slot_hits[cmc_key] += 1

        # Type hits
        type_found = set()
        for card in hand:
            type_line = card.get("type_line", "")
            for t in ["Creature", "Instant", "Sorcery", "Enchantment", "Artifact", "Planeswalker", "Land"]:
                if t in type_line and t not in type_found:
                    type_hits[t] += 1
                    type_found.add(t)

        # Color availability from lands
        colors_available = set()
        for land in lands_in_hand:
            for color in land.get("color_identity", []):
                colors_available.add(color)
            oracle = land.get("oracle_text", "").lower()
            if "any color" in oracle or "any type" in oracle:
                colors_available.update(["W", "U", "B", "R", "G"])

        for color in colors_available:
            color_in_hand[color] += 1

        # Playable turn 1
        has_one_drop = any(int(s.get("cmc", 0)) == 1 for s in spells_in_hand)
        if num_lands >= 1 and has_one_drop:
            playable_turn_1 += 1

        # Playable turn 2
        has_two_drop = any(int(s.get("cmc", 0)) <= 2 for s in spells_in_hand)
        if num_lands >= 2 and has_two_drop:
            playable_turn_2 += 1

        # Save sample hands (first 5)
        if i < 5:
            sample_hands.append({
                "hand_number": i + 1,
                "cards": [
                    {
                        "name": c.get("name", "Unknown"),
                        "mana_cost": c.get("mana_cost", ""),
                        "type_line": c.get("type_line", ""),
                        "cmc": c.get("cmc", 0),
                        "image_uri": c.get("image_uris", {}).get("small", ""),
                    }
                    for c in hand
                ],
                "lands": num_lands,
                "spells": len(spells_in_hand),
            })

    # Convert counts to probabilities
    n = n_simulations

    land_distribution = {}
    for num_lands in range(8):
        count = land_counts.get(num_lands, 0)
        land_distribution[str(num_lands)] = {
            "count": count,
            "probability": round(count / n * 100, 1),
        }

    cmc_probabilities = {}
    for cmc in range(8):
        count = cmc_slot_hits.get(cmc, 0)
        label = f"{cmc}" if cmc < 7 else "7+"
        cmc_probabilities[label] = {
            "count": count,
            "probability": round(count / n * 100, 1),
        }

    type_probabilities = {}
    for t in ["Creature", "Instant", "Sorcery", "Enchantment", "Artifact", "Planeswalker", "Land"]:
        count = type_hits.get(t, 0)
        type_probabilities[t] = {
            "count": count,
            "probability": round(count / n * 100, 1),
        }

    color_probabilities = {}
    for color in ["W", "U", "B", "R", "G"]:
        count = color_in_hand.get(color, 0)
        color_probabilities[color] = {
            "count": count,
            "probability": round(count / n * 100, 1),
        }

    return {
        "simulations": n,
        "hand_size": mulligan_to,
        "deck_size": len(deck),
        "land_distribution": land_distribution,
        "keepable_hand_rate": round(keepable_hands / n * 100, 1),
        "playable_turn_1_rate": round(playable_turn_1 / n * 100, 1),
        "playable_turn_2_rate": round(playable_turn_2 / n * 100, 1),
        "cmc_slot_probabilities": cmc_probabilities,
        "type_probabilities": type_probabilities,
        "color_access_probabilities": color_probabilities,
        "sample_hands": sample_hands,
    }


def simulate_mulligan_sequence(cards: list, n_simulations: int = 1000) -> dict:
    """
    Simulate the London mulligan decision process.
    For each simulation: draw 7, evaluate, mulligan to 6 if bad, then to 5.
    Tracks how often you need to mulligan and final hand quality.
    """
    if not cards:
        return {"error": "No cards to simulate"}

    deck = []
    for card_entry in cards:
        card_data = card_entry["card_data"]
        quantity = card_entry.get("quantity", 1)
        for _ in range(quantity):
            deck.append(card_data)

    keep_at_7 = 0
    keep_at_6 = 0
    keep_at_5 = 0
    mull_to_4_or_less = 0

    for _ in range(n_simulations):
        shuffled = deck.copy()
        random.shuffle(shuffled)

        # Draw 7
        hand_7 = shuffled[:7]
        if _is_keepable(hand_7):
            keep_at_7 += 1
            continue

        # Mulligan to 6
        random.shuffle(shuffled)
        hand_6 = shuffled[:7]
        if _is_keepable(hand_6, lenient=True):
            keep_at_6 += 1
            continue

        # Mulligan to 5
        random.shuffle(shuffled)
        hand_5 = shuffled[:7]
        if _is_keepable(hand_5, lenient=True):
            keep_at_5 += 1
            continue

        mull_to_4_or_less += 1

    n = n_simulations
    return {
        "simulations": n,
        "keep_at_7": {"count": keep_at_7, "rate": round(keep_at_7 / n * 100, 1)},
        "keep_at_6": {"count": keep_at_6, "rate": round(keep_at_6 / n * 100, 1)},
        "keep_at_5": {"count": keep_at_5, "rate": round(keep_at_5 / n * 100, 1)},
        "mulligan_to_4_or_less": {"count": mull_to_4_or_less, "rate": round(mull_to_4_or_less / n * 100, 1)},
        "average_final_hand_size": round(
            (keep_at_7 * 7 + keep_at_6 * 6 + keep_at_5 * 5 + mull_to_4_or_less * 4) / n, 2
        ),
    }


def _is_keepable(hand: list, lenient: bool = False) -> bool:
    """
    Evaluate if a hand is keepable.
    Basic heuristic: 2-4 lands (or 1-5 if lenient for mulligans).
    """
    lands = sum(1 for c in hand if "Land" in c.get("type_line", ""))
    spells = len(hand) - lands

    if lenient:
        return 1 <= lands <= 5 and spells >= 1
    else:
        return 2 <= lands <= 4 and spells >= 2