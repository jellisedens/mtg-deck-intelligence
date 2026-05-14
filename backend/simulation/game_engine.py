"""
Goldfish game state simulator.
Simulates turns 1-10 with no opponent interaction.
Tracks mana development, board state, castability, and card composition.
"""

import random
from collections import defaultdict
from copy import deepcopy


def _safe_int(value, default=1):
    """Safely convert a value to int, handling strings and None."""
    if value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def _get_card_types(card):
    """Extract card types from type_line."""
    type_line = card.get("type_line", "")
    types = []
    if "Creature" in type_line:
        types.append("Creature")
    if "Instant" in type_line:
        types.append("Instant")
    if "Sorcery" in type_line:
        types.append("Sorcery")
    if "Enchantment" in type_line:
        types.append("Enchantment")
    if "Artifact" in type_line:
        types.append("Artifact")
    if "Planeswalker" in type_line:
        types.append("Planeswalker")
    if card.get("sim_tags", {}).get("is_land"):
        types.append("Land")
    return types


def _is_ramp_card(card):
    """Check if a card is a ramp piece based on sim_tags."""
    tags = card.get("sim_tags", {})
    if tags.get("mana_production") and not tags.get("is_land"):
        return True
    for action in tags.get("on_resolve", []):
        if action.get("action") == "search_land":
            return True
    for action in tags.get("on_etb", []):
        if action.get("action") == "search_land":
            return True
    return False


def _is_draw_card(card):
    """Check if a card draws cards based on sim_tags."""
    tags = card.get("sim_tags", {})
    for action in tags.get("on_resolve", []) + tags.get("on_etb", []):
        if action.get("action") == "draw":
            return True
    for effect in tags.get("static_effects", []):
        if "draw" in effect.get("effect", ""):
            return True
    return False


class GameState:
    """Tracks the state of a single simulated game."""

    def __init__(self):
        self.library = []
        self.hand = []
        self.battlefield_lands = []
        self.battlefield_permanents = []
        self.graveyard = []
        self.turn = 0
        self.lands_played_this_turn = 0
        self.max_land_drops = 1
        self.mana_pool = defaultdict(int)
        self.total_mana_available = 0
        self.spells_cast_this_turn = 0
        self.cost_reductions = []
        self.static_effects = []
        self.turn_log = []

    def available_mana(self) -> dict:
        """Calculate total available mana from lands and mana sources."""
        mana = defaultdict(int)

        for land in self.battlefield_lands:
            tags = land.get("sim_tags", {})
            prod = tags.get("mana_production")
            if not prod:
                continue
            if prod.get("produces_any"):
                mana["any"] += _safe_int(prod.get("amount", 1))
            elif prod.get("produces_choice"):
                for color in prod["produces_choice"]:
                    mana[f"choice_{color}"] += 1
                mana["flexible"] += 1
            elif prod.get("produces"):
                for color, amount in prod["produces"].items():
                    mana[color] += _safe_int(amount)

        for perm in self.battlefield_permanents:
            tags = perm.get("sim_tags", {})
            prod = tags.get("mana_production")
            if not prod:
                continue
            if prod.get("produces_any"):
                mana["any"] += _safe_int(prod.get("amount", 1))
            elif prod.get("produces_choice"):
                for color in prod["produces_choice"]:
                    mana[f"choice_{color}"] += 1
                mana["flexible"] += 1
            elif prod.get("produces"):
                for color, amount in prod["produces"].items():
                    mana[color] += _safe_int(amount)

        return dict(mana)

    def total_mana(self) -> int:
        """Total mana available from all sources."""
        mana = self.available_mana()
        total = 0
        for key, amount in mana.items():
            if key.startswith("choice_"):
                continue
            total += amount
        return total

    def color_sources(self) -> dict:
        """Count how many sources produce each color."""
        sources = defaultdict(int)

        for land in self.battlefield_lands:
            tags = land.get("sim_tags", {})
            prod = tags.get("mana_production")
            if not prod:
                continue
            if prod.get("produces_any"):
                for c in ["W", "U", "B", "R", "G"]:
                    sources[c] += 1
            elif prod.get("produces_choice"):
                for c in prod["produces_choice"]:
                    sources[c] += 1
            elif prod.get("produces"):
                for c in prod["produces"]:
                    if c in ["W", "U", "B", "R", "G"]:
                        sources[c] += 1

        for perm in self.battlefield_permanents:
            tags = perm.get("sim_tags", {})
            prod = tags.get("mana_production")
            if not prod:
                continue
            if prod.get("produces_any"):
                for c in ["W", "U", "B", "R", "G"]:
                    sources[c] += 1
            elif prod.get("produces_choice"):
                for c in prod["produces_choice"]:
                    sources[c] += 1
            elif prod.get("produces"):
                for c in prod["produces"]:
                    if c in ["W", "U", "B", "R", "G"]:
                        sources[c] += 1

        return dict(sources)

    def can_cast(self, card: dict) -> bool:
        """Check if a card can be cast with available mana."""
        tags = card.get("sim_tags", {})
        cost = tags.get("cast_cost")
        if not cost:
            return False

        total_needed = _safe_int(cost.get("total", 0), 0)
        colors_needed = cost.get("colors", {})

        # Apply cost reductions
        reduction = 0
        for red in self.cost_reductions:
            applies = red.get("applies_to", "all")
            card_type = card.get("type_line", "").lower()
            if applies == "all":
                reduction += _safe_int(red.get("amount", 0), 0)
            elif applies in card_type:
                reduction += _safe_int(red.get("amount", 0), 0)

        total_needed = max(0, total_needed - reduction)

        # Check total mana
        total_available = self.total_mana()
        if total_available < total_needed:
            return False

        # If no colored mana required, we're good
        if not colors_needed:
            return True

        # Check color requirements
        sources = self.color_sources()

        for color, needed in colors_needed.items():
            needed = _safe_int(needed)
            dedicated = sources.get(color, 0)
            if dedicated >= needed:
                continue

            any_count = 0
            for land in self.battlefield_lands:
                prod = land.get("sim_tags", {}).get("mana_production", {})
                if prod and prod.get("produces_any"):
                    any_count += 1
            for perm in self.battlefield_permanents:
                prod = perm.get("sim_tags", {}).get("mana_production", {})
                if prod and prod.get("produces_any"):
                    any_count += 1

            if dedicated + any_count >= needed:
                continue

            return False

        return True

    def total_power_on_board(self) -> int:
        """Sum of power of all creatures on the battlefield."""
        total = 0
        for perm in self.battlefield_permanents:
            tags = perm.get("sim_tags", {})
            power = tags.get("power")
            if power is not None:
                total += _safe_int(power, 0)
        return total


def simulate_game(deck_cards: list, sim_tags: dict, turns: int = 10,
                  min_lands: int = 2, max_lands: int = 5) -> dict:
    """
    Simulate a single goldfish game.

    Args:
        deck_cards: list of card dicts with card_data and quantity
        sim_tags: dict of card_name (lowercase) -> sim_tags
        turns: number of turns to simulate
        min_lands: minimum lands in opening hand before mulligan
        max_lands: maximum lands in opening hand before mulligan

    Returns:
        dict with per-turn state snapshots and card composition tracking
    """
    # Build the deck
    library = []
    for card_entry in deck_cards:
        card_data = card_entry["card_data"]
        tags = sim_tags.get(card_data.get("name", "").lower(), {})
        card_with_tags = {**card_data, "sim_tags": tags}
        for _ in range(card_entry.get("quantity", 1)):
            library.append(card_with_tags)

    random.shuffle(library)

    state = GameState()
    state.library = library

    # Draw opening hand of 7
    for _ in range(7):
        if state.library:
            state.hand.append(state.library.pop(0))

    # Evaluate mulligan with configurable land thresholds
    lands_in_hand = sum(1 for c in state.hand if c.get("sim_tags", {}).get("is_land"))
    mulliganed = False
    if lands_in_hand < min_lands or lands_in_hand > max_lands:
        state.library.extend(state.hand)
        state.hand = []
        random.shuffle(state.library)
        for _ in range(6):
            if state.library:
                state.hand.append(state.library.pop(0))
        mulliganed = True

    # Track all cards seen cumulatively
    cards_seen = list(state.hand)

    # Opening hand composition
    opening_hand_types = defaultdict(int)
    opening_hand_has_ramp = False
    opening_hand_has_draw = False
    for c in state.hand:
        for t in _get_card_types(c):
            opening_hand_types[t] += 1
        if _is_ramp_card(c):
            opening_hand_has_ramp = True
        if _is_draw_card(c):
            opening_hand_has_draw = True

    turn_snapshots = []

    for turn_num in range(1, turns + 1):
        state.turn = turn_num
        state.lands_played_this_turn = 0
        state.spells_cast_this_turn = 0

        # Check for additional land drop effects
        state.max_land_drops = 1
        for effect in state.static_effects:
            if effect.get("effect") == "additional_land_drop":
                state.max_land_drops += _safe_int(effect.get("count", 1))

        # DRAW (skip turn 1)
        drawn_this_turn = None
        if turn_num > 1 and state.library:
            drawn = state.library.pop(0)
            state.hand.append(drawn)
            cards_seen.append(drawn)
            drawn_this_turn = drawn

        # Record pre-cast castability
        pre_cast_castable = sum(1 for c in state.hand
                                if not c.get("sim_tags", {}).get("is_land") and state.can_cast(c))

        # PLAY LAND
        _play_land(state)

        # Re-check after land drop
        post_land_castable = sum(1 for c in state.hand
                                 if not c.get("sim_tags", {}).get("is_land") and state.can_cast(c))

        # Castability tracking — what can we actually cast right now
        castable_by_type = defaultdict(int)
        castable_ramp = 0
        castable_draw = 0
        for c in state.hand:
            if c.get("sim_tags", {}).get("is_land"):
                continue
            if state.can_cast(c):
                for t in _get_card_types(c):
                    castable_by_type[t] += 1
                if _is_ramp_card(c):
                    castable_ramp += 1
                if _is_draw_card(c):
                    castable_draw += 1

        # Capture castable card names before casting
        pre_cast_castable_names = [c.get("name", "").lower() for c in state.hand if not c.get("sim_tags", {}).get("is_land") and state.can_cast(c)]

        # CAST SPELLS in priority order
        _cast_spells(state)

        # CAST SPELLS in priority order
        _cast_spells(state)

        # Cumulative card composition tracking
        cumulative_types = defaultdict(int)
        cumulative_ramp = 0
        cumulative_draw = 0
        for c in cards_seen:
            for t in _get_card_types(c):
                cumulative_types[t] += 1
            if _is_ramp_card(c):
                cumulative_ramp += 1
            if _is_draw_card(c):
                cumulative_draw += 1

        # Record snapshot
        snapshot = {
            "turn": turn_num,
            "lands_on_board": len(state.battlefield_lands),
            "total_mana_available": state.total_mana(),
            "color_sources": state.color_sources(),
            "cards_in_hand": len(state.hand),
            "creatures_on_board": sum(1 for p in state.battlefield_permanents
                                     if "Creature" in p.get("type_line", "")),
            "total_power_on_board": state.total_power_on_board(),
            "permanents_on_board": len(state.battlefield_permanents),
            "spells_cast": state.spells_cast_this_turn,
            "castable_before_casting": pre_cast_castable,
            "castable_after_land": post_land_castable,
            "uncastable_cards": sum(1 for c in state.hand
                                   if not c.get("sim_tags", {}).get("is_land") and not state.can_cast(c)),
            "cards_stuck_in_hand": sum(1 for c in state.hand
                                       if not c.get("sim_tags", {}).get("is_land")),
            "cumulative_types_seen": dict(cumulative_types),
            "cumulative_ramp_seen": cumulative_ramp,
            "cumulative_draw_seen": cumulative_draw,
            "total_cards_seen": len(cards_seen),
            "draw_types": {t: True for t in _get_card_types(drawn_this_turn)} if drawn_this_turn else {},
            "draw_is_ramp": _is_ramp_card(drawn_this_turn) if drawn_this_turn else False,
            "draw_is_draw": _is_draw_card(drawn_this_turn) if drawn_this_turn else False,
            "castable_by_type": dict(castable_by_type),
            "castable_ramp": castable_ramp,
            "castable_draw": castable_draw,
            "hand_card_names": [c.get("name", "").lower() for c in state.hand if not c.get("sim_tags", {}).get("is_land")],
            "castable_cards": pre_cast_castable_names,
            "cards_seen_names": [c.get("name", "").lower() for c in cards_seen if not c.get("sim_tags", {}).get("is_land")],
        }
        turn_snapshots.append(snapshot)

    return {
        "turns": turn_snapshots,
        "mulliganed": mulliganed,
        "opening_hand": {
            "types": dict(opening_hand_types),
            "has_ramp": opening_hand_has_ramp,
            "has_draw": opening_hand_has_draw,
            "land_count": opening_hand_types.get("Land", 0),
            "size": len(state.hand) if mulliganed else 7,
        },
        "final_state": {
            "lands": len(state.battlefield_lands),
            "permanents": len(state.battlefield_permanents),
            "cards_in_hand": len(state.hand),
            "library_remaining": len(state.library),
            "total_power": state.total_power_on_board(),
        },
    }


def _play_land(state: GameState):
    """Play a land from hand if possible."""
    while state.lands_played_this_turn < state.max_land_drops:
        best_land = None
        best_idx = None

        for i, card in enumerate(state.hand):
            tags = card.get("sim_tags", {})
            if tags.get("is_land"):
                if best_land is None:
                    best_land = card
                    best_idx = i
                else:
                    if not tags.get("enters_tapped") and best_land.get("sim_tags", {}).get("enters_tapped"):
                        best_land = card
                        best_idx = i

        if best_land is None:
            break

        state.hand.pop(best_idx)
        state.battlefield_lands.append(best_land)
        state.lands_played_this_turn += 1

        tags = best_land.get("sim_tags", {})
        for action in tags.get("on_etb", []):
            _execute_action(state, action)

        for effect in tags.get("static_effects", []):
            state.static_effects.append(effect)


def _cast_spells(state: GameState):
    """Cast spells from hand in priority order."""
    cast_order = _prioritize_hand(state)

    for card_idx in cast_order:
        if card_idx >= len(state.hand):
            continue
        card = state.hand[card_idx]
        tags = card.get("sim_tags", {})

        if tags.get("is_land"):
            continue

        if not state.can_cast(card):
            continue

        state.hand.pop(card_idx)
        state.spells_cast_this_turn += 1

        if tags.get("permanent"):
            state.battlefield_permanents.append(card)

            for action in tags.get("on_etb", []):
                _execute_action(state, action)

            for effect in tags.get("static_effects", []):
                if effect.get("effect") == "cost_reduction":
                    state.cost_reductions.append(effect)
                else:
                    state.static_effects.append(effect)
        else:
            for action in tags.get("on_resolve", []):
                _execute_action(state, action)
            state.graveyard.append(card)

        return _cast_spells(state)


def _prioritize_hand(state: GameState) -> list:
    """Return hand indices sorted by cast priority."""
    priorities = []

    for i, card in enumerate(state.hand):
        tags = card.get("sim_tags", {})
        if tags.get("is_land"):
            continue

        score = 50

        if tags.get("mana_production"):
            score = 10

        for effect in tags.get("static_effects", []):
            if effect.get("effect") == "cost_reduction":
                score = 15
                break

        has_draw = False
        for action in tags.get("on_resolve", []) + tags.get("on_etb", []):
            if action.get("action") == "draw":
                has_draw = True
                break
        for effect in tags.get("static_effects", []):
            if "draw" in effect.get("effect", ""):
                has_draw = True
                break
        if has_draw:
            score = 20

        for action in tags.get("on_resolve", []) + tags.get("on_etb", []):
            if action.get("action") == "search_land":
                score = 12
                break

        type_line = card.get("type_line", "")
        if "Creature" in type_line:
            score = 30

        priorities.append((i, score))

    priorities.sort(key=lambda x: x[1])
    return [p[0] for p in priorities]


def _execute_action(state: GameState, action: dict):
    """Execute a simulation action with safe type coercion."""
    act = action.get("action")

    if act == "draw":
        count = _safe_int(action.get("count", 1))
        for _ in range(count):
            if state.library:
                state.hand.append(state.library.pop(0))

    elif act == "put_back":
        count = _safe_int(action.get("count", 1))
        dest = action.get("destination", "top_of_library")
        for _ in range(min(count, len(state.hand))):
            if state.hand:
                card = state.hand.pop()
                if dest == "top_of_library":
                    state.library.insert(0, card)
                else:
                    state.library.append(card)

    elif act == "search_land":
        count = _safe_int(action.get("count", 1))
        dest = action.get("destination", "battlefield")
        land_type = action.get("land_type", "basic")
        enters_tapped = action.get("enters_tapped", False)

        for _ in range(count):
            land_idx = None
            for j, card in enumerate(state.library):
                card_tags = card.get("sim_tags", {})
                if card_tags.get("is_land"):
                    if land_type == "basic" and "Basic" not in card.get("type_line", ""):
                        continue
                    if land_type == "forest" and "Forest" not in card.get("type_line", ""):
                        continue
                    land_idx = j
                    break

            if land_idx is not None:
                land_card = state.library.pop(land_idx)
                if dest == "battlefield":
                    state.battlefield_lands.append(land_card)
                elif dest == "hand":
                    state.hand.append(land_card)

    elif act == "shuffle_library":
        random.shuffle(state.library)

    elif act == "create_token":
        count = _safe_int(action.get("count", 1))
        token = action.get("token", {})
        for _ in range(count):
            if token.get("type") == "Treasure":
                state.battlefield_permanents.append({
                    "name": "Treasure Token",
                    "type_line": "Artifact - Treasure",
                    "sim_tags": {
                        "permanent": True,
                        "mana_production": {"produces_any": True, "amount": 1, "type": "sacrifice"},
                    },
                })
            elif token.get("type") == "Creature":
                state.battlefield_permanents.append({
                    "name": f"{_safe_int(token.get('power', 1))}/{_safe_int(token.get('toughness', 1))} Token",
                    "type_line": "Creature Token",
                    "sim_tags": {
                        "permanent": True,
                        "power": _safe_int(token.get("power", 1)),
                        "toughness": _safe_int(token.get("toughness", 1)),
                    },
                })

    elif act == "scry":
        count = _safe_int(action.get("count", 1))
        for _ in range(min(count, len(state.library))):
            card = state.library[0]
            lands_on_board = len(state.battlefield_lands)
            if card.get("sim_tags", {}).get("is_land") and lands_on_board >= 4:
                state.library.pop(0)
                state.library.append(card)

    elif act == "deal_damage":
        pass

    elif act == "add_mana":
        pass

    elif act == "destroy" or act == "exile":
        pass


def run_simulation(deck_cards, sim_tags, n_games=100, turns=10, min_lands=2, max_lands=5):
    """
    Run N goldfish games and aggregate results.
    Returns averaged statistics per turn across all games,
    plus card composition tracking and opening hand analysis.
    """
    all_games = []
    for _ in range(n_games):
        game = simulate_game(deck_cards, sim_tags, turns, min_lands, max_lands)
        all_games.append(game)

    n = len(all_games)
    aggregated_turns = []

    # Track card types seen: per type, what % of games have seen at least one by each turn
    card_types = ["Creature", "Instant", "Sorcery", "Enchantment", "Artifact", "Planeswalker", "Land"]

    for turn_idx in range(turns):
        turn_stats = defaultdict(float)
        on_curve_count = 0
        all_colors_count = 0
        color_totals = defaultdict(float)

        # Card composition aggregation
        type_seen_counts = defaultdict(int)  # games where at least 1 of this type seen
        type_total_counts = defaultdict(float)  # total count across games
        ramp_seen_total = 0
        draw_seen_total = 0
        ramp_at_least_one = 0
        draw_at_least_one = 0

        for game in all_games:
            if turn_idx < len(game["turns"]):
                snapshot = game["turns"][turn_idx]
                for key, value in snapshot.items():
                    if key == "turn":
                        continue
                    if key == "color_sources":
                        for color, count in value.items():
                            color_totals[color] += count
                        continue
                    if key in ("cumulative_types_seen", "cumulative_ramp_seen",
                               "cumulative_draw_seen", "total_cards_seen",
                               "draw_types", "draw_is_ramp", "draw_is_draw",
                               "castable_by_type", "castable_ramp", "castable_draw",
                               "cards_in_hand", "cards_seen_names", "castable_cards", "hand_card_names"):
                        continue
                    turn_stats[key] += value

                if snapshot.get("spells_cast", 0) > 0:
                    on_curve_count += 1

                sources = snapshot.get("color_sources", {})
                if all(sources.get(c, 0) > 0 for c in ["W", "U", "B", "R", "G"]):
                    all_colors_count += 1

                # Card composition tracking
                types_seen = snapshot.get("cumulative_types_seen", {})
                for card_type in card_types:
                    count = types_seen.get(card_type, 0)
                    type_total_counts[card_type] += count
                    if count > 0:
                        type_seen_counts[card_type] += 1

                # Per-turn draw tracking (what was drawn THIS turn)
                draw_types_this = snapshot.get("draw_types", {})
                for card_type in card_types:
                    if draw_types_this.get(card_type):
                        if f"draw_{card_type}" not in turn_stats:
                            turn_stats[f"draw_{card_type}"] = 0
                        turn_stats[f"draw_{card_type}"] += 1        

                ramp_count = snapshot.get("cumulative_ramp_seen", 0)
                draw_count = snapshot.get("cumulative_draw_seen", 0)
                ramp_seen_total += ramp_count
                draw_seen_total += draw_count
                if ramp_count > 0:
                    ramp_at_least_one += 1
                if draw_count > 0:
                    draw_at_least_one += 1

        # Average the stats
        averaged = {"turn": turn_idx + 1}
        for key, total in turn_stats.items():
            averaged[f"avg_{key}"] = round(total / n, 2)

        averaged["avg_color_sources"] = {}
        for color in ["W", "U", "B", "R", "G", "C"]:
            if color in color_totals:
                averaged["avg_color_sources"][color] = round(color_totals[color] / n, 2)

        averaged["on_curve_rate"] = round(on_curve_count / n * 100, 1)
        averaged["all_colors_rate"] = round(all_colors_count / n * 100, 1)

        color_access = {}
        for color in ["W", "U", "B", "R", "G"]:
            has_color = 0
            for game in all_games:
                if turn_idx < len(game["turns"]):
                    sources = game["turns"][turn_idx].get("color_sources", {})
                    if sources.get(color, 0) > 0:
                        has_color += 1
            color_access[color] = round(has_color / n * 100, 1)
        averaged["color_access_rates"] = color_access

        mana_deficit_count = 0
        for game in all_games:
            if turn_idx < len(game["turns"]):
                mana = game["turns"][turn_idx].get("total_mana_available", 0)
                if mana < turn_idx + 1:
                    mana_deficit_count += 1
        averaged["mana_on_curve_rate"] = round((n - mana_deficit_count) / n * 100, 1)

        # Card composition stats for this turn
        composition = {}
        for card_type in card_types:
            composition[card_type] = {
                "avg_seen": round(type_total_counts[card_type] / n, 2),
                "pct_at_least_one": round(type_seen_counts[card_type] / n * 100, 1),
            }
        composition["Ramp"] = {
            "avg_seen": round(ramp_seen_total / n, 2),
            "pct_at_least_one": round(ramp_at_least_one / n * 100, 1),
        }
        composition["Card Draw"] = {
            "avg_seen": round(draw_seen_total / n, 2),
            "pct_at_least_one": round(draw_at_least_one / n * 100, 1),
        }
        averaged["card_composition"] = composition

        # What was drawn this specific turn (% chance of drawing each type)
        draw_rates = {}
        for card_type in card_types:
            key = f"draw_{card_type}"
            count = turn_stats.get(key, 0)
            draw_rates[card_type] = round(count / n * 100, 1)
        averaged["draw_rate_this_turn"] = draw_rates

        aggregated_turns.append(averaged)

    # Opening hand aggregation
    mulligan_count = sum(1 for g in all_games if g.get("mulliganed", False))
    opening_type_totals = defaultdict(float)
    opening_ramp_count = 0
    opening_draw_count = 0

    for game in all_games:
        oh = game.get("opening_hand", {})
        for t, count in oh.get("types", {}).items():
            opening_type_totals[t] += count
        if oh.get("has_ramp"):
            opening_ramp_count += 1
        if oh.get("has_draw"):
            opening_draw_count += 1

    opening_hand_stats = {
        "mulligan_rate": round(mulligan_count / n * 100, 1),
        "avg_types": {t: round(v / n, 2) for t, v in opening_type_totals.items()},
        "pct_has_ramp": round(opening_ramp_count / n * 100, 1),
        "pct_has_draw": round(opening_draw_count / n * 100, 1),
    }

    return {
        "games_simulated": n,
        "turns_per_game": turns,
        "mulligan_settings": {"min_lands": min_lands, "max_lands": max_lands},
        "opening_hand_stats": opening_hand_stats,
        "per_turn_averages": aggregated_turns,
    }