"""
New suggest pipeline — tag-based card discovery.

Replaces oracle text pattern matching with:
1. AI tag classifier (prompt → categories)
2. Tagged EDHREC pool (primary source, cached after first resolve)
3. Scryfall otag: search (fills gaps)
4. Oracle text fallback (untagged cards)
"""

import os
import re
import json
import time
import asyncio
from openai import OpenAI
from services.tag_index import get_card_tags, is_index_loaded
from services.tag_classifier import classify_tags, filter_by_category
from services.scryfall import scryfall_service
from services.edhrec import fetch_commander_profile
from services.prompt_constraints import extract_deterministic_constraints, apply_deterministic_constraints
from services.search_spec import generate_search_spec, apply_spec_filter
from data.scryfall_tags import CATEGORY_TAG_GROUPS

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL = "gpt-4o-mini"


async def suggest_with_tags(
    prompt: str,
    deck_cards: list,
    deck_info: dict,
    card_lookup: dict,
    edhrec_profile: dict = None,
    conversation_context: list = None,
) -> dict:
    """
    Tag-based suggest pipeline.

    Returns the same format as the current _handle_suggest:
    {
        "summary": str,
        "suggestions": [...],
        "cuts": [],
        "strategy_notes": str,
    }
    """
    t_start = time.time()

    # ── Step 1: Classify prompt into categories ──────────────
    t_classify = time.time()
    classification = classify_tags(prompt)
    categories = classification.get("categories", ["general"])
    is_specific = classification.get("is_specific", False)
    print(f"[TAG] Classified: {categories} (specific={is_specific}) ({time.time() - t_classify:.1f}s)")

    # ── Step 2: Build existing cards set ─────────────────────
    existing_cards = set()
    if deck_cards:
        for card in deck_cards:
            existing_cards.add(card.card_name.lower())

    # ── Step 3: Get color identity ───────────────────────────
    color_identity = []
    if deck_info:
        prefs = deck_info.get("preferences") or {}
        color_identity = prefs.get("color_identity", [])
    if not color_identity and deck_cards and card_lookup:
        for card in deck_cards:
            if card.board == "commander":
                card_data = card_lookup.get(card.scryfall_id, {})
                color_identity = card_data.get("color_identity", [])
                break

    # ── Step 4: Load and tag EDHREC pool ─────────────────────
    t_edhrec = time.time()
    edhrec_tagged = []

    if edhrec_profile:
        # Check for cached tagged pool first
        cached_pool = edhrec_profile.get("_tagged_pool")
        if cached_pool:
            # Use cached — filter out cards already in deck
            edhrec_tagged = [
                c for c in cached_pool
                if c["name"].lower() not in existing_cards
            ]
            print(f"[TAG] EDHREC pool (cached): {len(edhrec_tagged)} cards ({time.time() - t_edhrec:.1f}s)")
        else:
            # Resolve and tag all cards, then cache
            all_edhrec = []
            for card in edhrec_profile.get("cards", []):
                if card["name"].lower() not in existing_cards:
                    all_edhrec.append(card)

            if all_edhrec:
                for i in range(0, len(all_edhrec), 75):
                    batch = all_edhrec[i:i + 75]
                    identifiers = [{"name": c["name"]} for c in batch]
                    resolved = await scryfall_service.get_collection(identifiers)
                    if "data" in resolved:
                        lookup = {c["name"].lower(): c for c in batch}
                        for card_data in resolved["data"]:
                            name = card_data.get("name", "")
                            ecard = lookup.get(name.lower(), {})
                            oracle_id = card_data.get("oracle_id", "")
                            tags = get_card_tags(oracle_id) if is_index_loaded() else []

                            edhrec_tagged.append({
                                "name": name,
                                "mana_cost": card_data.get("mana_cost", ""),
                                "cmc": card_data.get("cmc", 0),
                                "type_line": card_data.get("type_line", ""),
                                "oracle_text": card_data.get("oracle_text", ""),
                                "colors": card_data.get("colors", []),
                                "color_identity": card_data.get("color_identity", []),
                                "rarity": card_data.get("rarity", ""),
                                "prices": card_data.get("prices", {}),
                                "image_uris": card_data.get("image_uris", {}),
                                "scryfall_id": card_data.get("id", ""),
                                "edhrec_rank": card_data.get("edhrec_rank"),
                                "power": card_data.get("power"),
                                "toughness": card_data.get("toughness"),
                                "keywords": card_data.get("keywords", []),
                                "tags": tags,
                                "oracle_id": oracle_id,
                                "_edhrec_proven": True,
                                "_edhrec_synergy": ecard.get("synergy", 0),
                                "_edhrec_inclusion_pct": ecard.get("inclusion_pct", 0),
                            })

                # Cache the tagged pool on the profile for next time
                _cache_tagged_pool(edhrec_profile, edhrec_tagged, deck_info)

            print(f"[TAG] EDHREC pool (resolved): {len(edhrec_tagged)} cards ({time.time() - t_edhrec:.1f}s)")

    # ── Step 5: Filter EDHREC pool by categories ─────────────
    if "general" not in categories:
        t_filter = time.time()
        edhrec_filtered = filter_by_category(edhrec_tagged, categories)
        # Sort by synergy + inclusion
        edhrec_filtered.sort(
            key=lambda c: (c.get("_edhrec_synergy", 0), c.get("_edhrec_inclusion_pct", 0)),
            reverse=True,
        )
        print(f"[TAG] EDHREC filtered: {len(edhrec_filtered)} match categories {categories} ({time.time() - t_filter:.1f}s)")
    else:
        # General request — sort by synergy
        edhrec_filtered = sorted(
            edhrec_tagged,
            key=lambda c: (c.get("_edhrec_synergy", 0), c.get("_edhrec_inclusion_pct", 0)),
            reverse=True,
        )
        print(f"[TAG] General request: {len(edhrec_filtered)} cards sorted by synergy")

    # ── Step 6: Scryfall otag: search (fills gaps) ───────────
    scryfall_results = []
    needs_scryfall = len(edhrec_filtered) < 15 or is_specific

    if needs_scryfall and "general" not in categories:
        t_scryfall = time.time()
        wubrg = "WUBRG"
        ci_str = "".join(c for c in wubrg if c in color_identity) if color_identity else ""
        ci_filter = f" id<={ci_str}" if ci_str else ""
        fmt_filter = f" f:{(deck_info or {}).get('format', 'commander')}"

        queries = []
        for cat in categories:
            tag_group = CATEGORY_TAG_GROUPS.get(cat, [])
            otag_names = []
            for tag in tag_group[:3]:
                otag = tag.replace(" ", "-").replace("'", "")
                otag_names.append(otag)

            for otag in otag_names[:2]:
                queries.append(f"otag:{otag}{fmt_filter}{ci_filter}")

        if queries:
            tasks = [scryfall_service.search_cards_raw(q) for q in queries]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            seen_names = {c["name"].lower() for c in edhrec_filtered}
            seen_names.update(existing_cards)

            for result in results:
                if isinstance(result, Exception) or "error" in result:
                    continue
                for card in result.get("data", []):
                    if card["name"].lower() not in seen_names:
                        oracle_id = card.get("oracle_id", "")
                        scryfall_results.append({
                            "name": card["name"],
                            "mana_cost": card.get("mana_cost", ""),
                            "cmc": card.get("cmc", 0),
                            "type_line": card.get("type_line", ""),
                            "oracle_text": card.get("oracle_text", ""),
                            "colors": card.get("colors", []),
                            "color_identity": card.get("color_identity", []),
                            "rarity": card.get("rarity", ""),
                            "prices": card.get("prices", {}),
                            "image_uris": card.get("image_uris", {}),
                            "scryfall_id": card["id"],
                            "edhrec_rank": card.get("edhrec_rank"),
                            "power": card.get("power"),
                            "toughness": card.get("toughness"),
                            "keywords": card.get("keywords", []),
                            "tags": get_card_tags(oracle_id) if is_index_loaded() else [],
                        })
                        seen_names.add(card["name"].lower())

            scryfall_results.sort(key=lambda c: c.get("edhrec_rank") or 999999)
            print(f"[TAG] Scryfall backfill: {len(scryfall_results)} cards ({time.time() - t_scryfall:.1f}s)")

    # ── Step 7: Merge results (EDHREC first) ─────────────────
    all_results = edhrec_filtered + scryfall_results

    # ── Step 8: Color identity filter ────────────────────────
    if color_identity:
        deck_ci = set(color_identity)
        before = len(all_results)
        all_results = [c for c in all_results if set(c.get("color_identity", [])).issubset(deck_ci)]
        removed = before - len(all_results)
        if removed:
            print(f"[TAG] Color identity filter removed {removed} cards")

    # ── Step 9: Deterministic constraints (CMC, price) ───────
    det_constraints = extract_deterministic_constraints(prompt)
    all_results = apply_deterministic_constraints(all_results, det_constraints)

    # ── Step 10: Spec filter for specific requests ───────────
    if is_specific:
        t_spec = time.time()
        ci_for_spec = color_identity
        fmt_for_spec = (deck_info or {}).get("format", "commander")
        search_spec = generate_search_spec(prompt, color_identity=ci_for_spec, deck_format=fmt_for_spec)
        if search_spec and not search_spec.get("error"):
            all_results = apply_spec_filter(all_results, search_spec)
            print(f"[TAG] Spec filter applied ({time.time() - t_spec:.1f}s)")

    # ── Step 11: Build AI prompt and pick ─────────────────────
    max_results = 8
    candidates = all_results[:30]

    slim = []
    for card in candidates:
        s = {
            "name": card["name"],
            "mana_cost": card.get("mana_cost", ""),
            "cmc": card.get("cmc", 0),
            "type_line": card.get("type_line", ""),
            "oracle_text": card.get("oracle_text", ""),
            "rarity": card.get("rarity", ""),
            "scryfall_id": card.get("scryfall_id", ""),
            "edhrec_rank": card.get("edhrec_rank"),
        }
        if card.get("_edhrec_proven"):
            s["edhrec_proven"] = True
            s["edhrec_synergy"] = card.get("_edhrec_synergy", 0)
            s["edhrec_inclusion_pct"] = card.get("_edhrec_inclusion_pct", 0)
        slim.append(s)

    # Build deck context summary
    deck_summary = ""
    if deck_info:
        name = deck_info.get("name", "")
        fmt = deck_info.get("format", "commander")
        profile = deck_info.get("strategy_profile") or {}
        strategy = profile.get("primary_strategy", "")
        deck_summary = f"Deck: {name} ({fmt})"
        if strategy:
            deck_summary += f", Strategy: {strategy}"

    system = f"""You are an expert Magic: The Gathering deck builder.
Pick the {max_results} best cards from the search results for the user's request.

{deck_summary}

Rules:
- ONLY pick cards from the search results below — never invent cards
- Cards marked ★PROVEN are used in real commander decks — STRONGLY PREFER these
- Higher synergy % means more effective with this specific commander
- Explain WHY each card fits the request and the deck's strategy
- Reference specific synergies with cards already in the deck

Respond with ONLY valid JSON:
{{
    "summary": "Brief deck context and what these cards do for it",
    "suggestions": [
        {{
            "card_name": "Exact Name",
            "scryfall_id": "id-from-results",
            "category": "ramp/removal/draw/protection/utility/creature/etc",
            "reasoning": "Why this card fits"
        }}
    ],
    "cuts": [],
    "strategy_notes": "Brief strategic advice"
}}"""

    user_msg = f"User request: {prompt}\n\n"
    user_msg += f"Search results ({len(slim)} cards):\n"
    for card in slim:
        price = card.get("prices", {}).get("usd", "N/A") if isinstance(card.get("prices"), dict) else "N/A"
        proven = ""
        if card.get("edhrec_proven"):
            proven = f" ★PROVEN ({card.get('edhrec_inclusion_pct', 0):.0f}% decks, {card.get('edhrec_synergy', 0):.0f}% synergy)"
        user_msg += f"- {card['name']} | {card['mana_cost']} | {card['type_line']} | ${price} | ID: {card.get('scryfall_id', '')}{proven}\n"
        if card.get("oracle_text"):
            user_msg += f"  Text: {card['oracle_text'][:150]}\n"

    print(f"[TAG] Prompt: {len(system)+len(user_msg)} chars (~{(len(system)+len(user_msg))//4} tokens)")

    t_ai = time.time()
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.5,
        )
        content = response.choices[0].message.content.strip()
        content = content.replace("```json", "").replace("```", "").strip()
        content = re.sub(r',\s*([}\]])', r'\1', content)
        result = json.loads(content)
    except Exception as e:
        print(f"[TAG] AI call failed: {e}")
        result = {"error": "ai_error", "details": str(e)}

    print(f"[TAG] AI pick ({time.time() - t_ai:.1f}s)")
    print(f"[TAG] Total: {time.time() - t_start:.1f}s")

    # Verify suggestions exist in our results
    result_lookup = {c.get("scryfall_id", ""): c for c in all_results}
    name_lookup = {c["name"].lower(): c for c in all_results}

    verified = []
    for suggestion in result.get("suggestions", []):
        card_data = result_lookup.get(suggestion.get("scryfall_id"))
        name_lower = suggestion.get("card_name", "").lower()

        if card_data and card_data.get("name", "").lower() == name_lower:
            sid = card_data.get("scryfall_id", "")
            suggestion["image_uri"] = card_data.get("image_uris", {}).get("normal", "") or f"https://api.scryfall.com/cards/{sid}?format=image&version=normal"
            suggestion["mana_cost"] = card_data.get("mana_cost", "")
            suggestion["type_line"] = card_data.get("type_line", "")
            suggestion["price_usd"] = card_data.get("prices", {}).get("usd")
            verified.append(suggestion)
        elif name_lower in name_lookup:
            correct = name_lookup[name_lower]
            sid = correct.get("scryfall_id", "")
            suggestion["scryfall_id"] = sid
            suggestion["image_uri"] = correct.get("image_uris", {}).get("normal", "") or f"https://api.scryfall.com/cards/{sid}?format=image&version=normal"
            suggestion["mana_cost"] = correct.get("mana_cost", "")
            suggestion["type_line"] = correct.get("type_line", "")
            suggestion["price_usd"] = correct.get("prices", {}).get("usd")
            verified.append(suggestion)

    result["suggestions"] = verified
    result.setdefault("cuts", [])
    result.setdefault("debug", {})
    result["debug"]["categories"] = categories
    result["debug"]["is_specific"] = is_specific
    result["debug"]["edhrec_pool"] = len(edhrec_tagged)
    result["debug"]["edhrec_filtered"] = len(edhrec_filtered)
    result["debug"]["scryfall_backfill"] = len(scryfall_results)
    result["debug"]["total_candidates"] = len(all_results)

    return result


def _cache_tagged_pool(edhrec_profile: dict, tagged_pool: list, deck_info: dict = None):
    """Cache the resolved + tagged EDHREC pool on the strategy profile."""
    try:
        slim_pool = []
        for card in tagged_pool:
            slim_pool.append({
                "name": card["name"],
                "mana_cost": card.get("mana_cost", ""),
                "cmc": card.get("cmc", 0),
                "type_line": card.get("type_line", ""),
                "oracle_text": card.get("oracle_text", ""),
                "colors": card.get("colors", []),
                "color_identity": card.get("color_identity", []),
                "rarity": card.get("rarity", ""),
                "scryfall_id": card.get("scryfall_id", ""),
                "edhrec_rank": card.get("edhrec_rank"),
                "power": card.get("power"),
                "toughness": card.get("toughness"),
                "tags": card.get("tags", []),
                "oracle_id": card.get("oracle_id", ""),
                "_edhrec_proven": True,
                "_edhrec_synergy": card.get("_edhrec_synergy", 0),
                "_edhrec_inclusion_pct": card.get("_edhrec_inclusion_pct", 0),
            })

        edhrec_profile["_tagged_pool"] = slim_pool
        print(f"[TAG] Cached tagged pool: {len(slim_pool)} cards")

        if deck_info:
            from database.session import SessionLocal
            from sqlalchemy import text

            profile = deck_info.get("strategy_profile") or {}
            profile["edhrec_profile"] = edhrec_profile
            deck_info["strategy_profile"] = profile

            deck_name = deck_info.get("name")
            if deck_name:
                db = SessionLocal()
                db.execute(
                    text("UPDATE decks SET strategy_profile = :profile WHERE name = :name"),
                    {"profile": json.dumps(profile), "name": deck_name},
                )
                db.commit()
                db.close()
                print(f"[TAG] Persisted tagged pool to database")
    except Exception as e:
        print(f"[TAG] Failed to cache tagged pool: {e}")