"""
Custom simulation metrics.
Post-processes simulation results to compute user-selected tracking metrics.
"""

from collections import defaultdict


def compute_custom_metrics(all_games: list, tracking_options: dict, deck_cards: list = None, sim_tags: dict = None, user_role_map: dict = None) -> dict:
    results = {}
    n_games = len(all_games)
    if n_games == 0:
        return results
    
    turns = len(all_games[0].get("turns", []))
    
    if tracking_options.get("track_roles"):
        results["role_tracking"] = _track_roles(
            all_games, tracking_options["track_roles"], turns, n_games, deck_cards, sim_tags, user_role_map
        )
    
    if tracking_options.get("track_types"):
        results["type_tracking"] = _track_types(
            all_games, tracking_options["track_types"], turns, n_games
        )
    
    if tracking_options.get("track_commander"):
        results["commander_tracking"] = _track_commander(
            all_games, tracking_options["track_commander"], turns, n_games
        )
    
    if tracking_options.get("track_cmc_slots"):
        results["cmc_tracking"] = _track_cmc_slots(
            all_games, tracking_options["track_cmc_slots"], turns, n_games, deck_cards
        )
    
    return results


def _track_roles(all_games: list, roles: list, turns: int, n_games: int, deck_cards: list, sim_tags: dict = None, user_role_map: dict = None) -> dict:
    """Track probability of having AND being able to cast cards of specific roles by each turn."""
    from simulation.game_engine import _is_ramp_card, _is_draw_card
    
    # Build role lookup — prioritize user tags, fall back to sim_tags
    role_cards = defaultdict(set)
    if deck_cards:
        for card_entry in deck_cards:
            card_data = card_entry.get("card_data", {})
            card_name = card_data.get("name", "").lower()
            
            # User-assigned roles take priority
            if user_role_map and card_name in user_role_map:
                for role in user_role_map[card_name]:
                    role_cards[role].add(card_name)
            elif not user_role_map:
                # Only fall back to sim_tags if NO user tags exist in the deck
                tags = {}
                if sim_tags:
                    tags = sim_tags.get(card_name, {})
                card_with_tags = {**card_data, "sim_tags": tags}
                
                if _is_ramp_card(card_with_tags):
                    role_cards["ramp"].add(card_name)
                if _is_draw_card(card_with_tags):
                    role_cards["card_draw"].add(card_name)
    
    tracking = {}
    for role in roles:
        role_card_names = role_cards.get(role, set())
        
        per_turn_drawn = defaultdict(int)
        per_turn_castable = defaultdict(int)
        per_turn_count = defaultdict(float)
        
        for game in all_games:
            for turn_idx, snapshot in enumerate(game.get("turns", [])):
                turn_num = turn_idx + 1
                
                if role == "ramp" and not user_role_map:
                    count = snapshot.get("cumulative_ramp_seen", 0)
                    if count > 0:
                        per_turn_drawn[turn_num] += 1
                    per_turn_count[turn_num] += count
                    castable = snapshot.get("castable_ramp", 0)
                    if castable > 0:
                        per_turn_castable[turn_num] += 1
                elif role == "card_draw" and not user_role_map:
                    count = snapshot.get("cumulative_draw_seen", 0)
                    if count > 0:
                        per_turn_drawn[turn_num] += 1
                    per_turn_count[turn_num] += count
                    castable = snapshot.get("castable_draw", 0)
                    if castable > 0:
                        per_turn_castable[turn_num] += 1
                else:
                    # User-tagged roles — use card names from snapshot
                    seen_names = snapshot.get("cards_seen_names", [])
                    castable_names = snapshot.get("castable_cards", [])
                    
                    # Count how many role cards have been seen
                    seen_count = sum(1 for name in seen_names if name in role_card_names)
                    if seen_count > 0:
                        per_turn_drawn[turn_num] += 1
                    per_turn_count[turn_num] += seen_count
                    
                    # Count how many role cards are castable in hand
                    castable_count = sum(1 for name in castable_names if name in role_card_names)
                    if castable_count > 0:
                        per_turn_castable[turn_num] += 1
        
        tracking[role] = {
            "per_turn_drawn_pct": {
                str(t): round(per_turn_drawn[t] / n_games * 100, 1) for t in range(1, turns + 1)
            },
            "per_turn_castable_pct": {
                str(t): round(per_turn_castable[t] / n_games * 100, 1) for t in range(1, turns + 1)
            },
            "per_turn_avg_count": {
                str(t): round(per_turn_count[t] / n_games, 2) for t in range(1, turns + 1)
            },
            "cards_in_deck": len(role_card_names),
            "card_names": sorted(list(role_card_names))[:10],
        }
    
    return tracking


def _track_types(all_games: list, types: list, turns: int, n_games: int) -> dict:
    tracking = {}
    
    for card_type in types:
        per_turn_has = defaultdict(int)
        per_turn_count = defaultdict(float)
        per_turn_castable = defaultdict(int)
        
        for game in all_games:
            for turn_idx, snapshot in enumerate(game.get("turns", [])):
                turn_num = turn_idx + 1
                types_seen = snapshot.get("cumulative_types_seen", {})
                count = types_seen.get(card_type, 0)
                per_turn_count[turn_num] += count
                if count > 0:
                    per_turn_has[turn_num] += 1
                castable = snapshot.get("castable_by_type", {}).get(card_type, 0)
                if castable > 0:
                    per_turn_castable[turn_num] += 1
        
        tracking[card_type] = {
            "per_turn_drawn_pct": {
                str(t): round(per_turn_has[t] / n_games * 100, 1) for t in range(1, turns + 1)
            },
            "per_turn_castable_pct": {
                str(t): round(per_turn_castable[t] / n_games * 100, 1) for t in range(1, turns + 1)
            },
            "per_turn_avg_count": {
                str(t): round(per_turn_count[t] / n_games, 2) for t in range(1, turns + 1)
            },
        }
    
    return tracking


def _track_commander(all_games: list, commander_info: dict, turns: int, n_games: int) -> dict:
    cmc = commander_info.get("cmc", 0)
    colors_needed = commander_info.get("colors", {})
    
    per_turn_castable = defaultdict(int)
    
    for game in all_games:
        for turn_idx, snapshot in enumerate(game.get("turns", [])):
            turn_num = turn_idx + 1
            total_mana = snapshot.get("total_mana_available", 0)
            color_sources = snapshot.get("color_sources", {})
            
            has_mana = total_mana >= cmc
            has_colors = all(
                color_sources.get(color, 0) >= count
                for color, count in colors_needed.items()
            )
            
            if has_mana and has_colors:
                per_turn_castable[turn_num] += 1
    
    return {
        "commander_cmc": cmc,
        "colors_required": colors_needed,
        "per_turn_castable_pct": {
            str(t): round(per_turn_castable[t] / n_games * 100, 1) for t in range(1, turns + 1)
        },
    }


def _track_cmc_slots(all_games: list, cmc_slots: list, turns: int, n_games: int, deck_cards: list) -> dict:
    cmc_card_counts = defaultdict(int)
    if deck_cards:
        for card_entry in deck_cards:
            card_data = card_entry.get("card_data", {})
            if "Land" in card_data.get("type_line", ""):
                continue
            card_cmc = int(card_data.get("cmc", 0))
            cmc_card_counts[card_cmc] += card_entry.get("quantity", 1)
    
    tracking = {}
    for cmc in cmc_slots:
        per_turn_has = defaultdict(int)
        
        for game in all_games:
            for turn_idx, snapshot in enumerate(game.get("turns", [])):
                turn_num = turn_idx + 1
                total_mana = snapshot.get("total_mana_available", 0)
                castable_before = snapshot.get("castable_before_casting", 0)
                
                if total_mana >= cmc and castable_before > 0:
                    per_turn_has[turn_num] += 1
        
        tracking[str(cmc)] = {
            "cards_at_cmc": cmc_card_counts.get(cmc, 0),
            "per_turn_can_cast_pct": {
                str(t): round(per_turn_has[t] / n_games * 100, 1) for t in range(1, turns + 1)
            },
        }
    
    return tracking