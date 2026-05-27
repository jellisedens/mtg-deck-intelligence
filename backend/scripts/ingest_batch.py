"""
MTG Card Ingest Script — Batch API Version
Uses OpenAI's Batch API for 50% cost reduction and no rate limit concerns.

Workflow:
  Step 1: python scripts/ingest_batch.py prepare    — builds batch file and uploads
  Step 2: python scripts/ingest_batch.py status      — check batch progress
  Step 3: python scripts/ingest_batch.py complete     — download results, embed, store

The batch typically completes within 1-2 hours (max 24 hours).
"""

import os
import sys
import json
import time
import re
import argparse
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx
from openai import OpenAI
from sqlalchemy import text

from database.session import SessionLocal
from models.card import Card

SCRYFALL_HEADERS = {
    "User-Agent": "MTGDeckIntelligence/1.0",
    "Accept": "application/json",
}

CACHE_DIR = Path("/tmp/mtg_ingest_cache")
BULK_CACHE = CACHE_DIR / "oracle_cards_v2.json"
TAGS_CACHE = CACHE_DIR / "ai_tags_v2.json"
BATCH_FILE = CACHE_DIR / "batch_requests.jsonl"
BATCH_ID_FILE = CACHE_DIR / "batch_id.txt"
BATCH_RESULTS_FILE = CACHE_DIR / "batch_results.jsonl"

client = OpenAI()

# ── Allowed values for validation (same as v2) ────────

ALLOWED_ROLES = {
    "ramp", "mana_fixing", "mana_rock", "mana_dork", "card_draw", "card_advantage",
    "card_selection", "cantrip", "removal_single", "removal_board_wipe", "removal_exile",
    "removal_damage", "counterspell", "protection", "hexproof_enabler",
    "indestructible_enabler", "tutor", "recursion", "sacrifice_outlet", "death_trigger",
    "etb_trigger", "attack_trigger", "upkeep_trigger", "finisher", "win_condition",
    "combo_piece", "stax", "tax_effect", "pillowfort", "evasion", "token_generator",
    "anthem", "lifegain", "lifegain_payoff", "graveyard_fill", "self_mill",
    "reanimation", "reanimation_target", "artifact_hate", "enchantment_hate",
    "land_destruction", "hate_piece", "utility", "equipment", "aura", "land",
    "color_fixing_land", "utility_land", "cost_reducer", "ritual", "pump",
    "combat_trick", "looting", "wheel", "clone", "theft", "blink", "flicker",
    "graveyard_hate", "politics", "goad", "monarch", "initiative",
}

ALLOWED_ARCHETYPES = {
    "aristocrats", "tokens", "voltron", "spellslinger", "storm", "reanimator",
    "mill", "control", "aggro", "midrange", "group_hug", "group_slug", "stax",
    "tribal", "landfall", "enchantress", "artifacts_matter", "equipment_matters",
    "blink", "clone", "theft", "politics", "combo", "goodstuff", "any_deck",
    "superfriends", "life_drain", "wheels", "infect", "chaos", "graveyard",
    "sacrifice", "ramp_heavy", "big_mana", "stompy", "burn", "hatebears",
    "pillowfort", "turbo_fog", "counters_matter", "energy", "treasure",
}

ALLOWED_POWER_LEVELS = {
    "format_staple", "color_staple", "archetype_staple", "niche",
}

TAGGING_SYSTEM_PROMPT = """You are an expert Magic: The Gathering deck builder with deep knowledge of Commander/EDH.

For each card, generate strategic metadata that captures what experienced players know — not just card text, but HOW and WHY decks use this card.

Respond with ONLY a JSON array, no markdown backticks, no explanation:
[
  {
    "name": "Card Name",
    "roles": ["role1", "role2"],
    "archetypes": ["archetype1", "archetype2"],
    "power_level": "format_staple|color_staple|archetype_staple|niche",
    "search_terms": ["term1", "term2", "term3", "term4", "term5"],
    "synergies": ["synergy1", "synergy2"],
    "summary": "One sentence capturing strategic value from an experienced player's perspective."
  }
]

IMPORTANT RULES:
- search_terms should be 4-6 terms that a PLAYER would type when looking for this card's EFFECT
- Do NOT include the card's own name in search_terms
- Think: "what problem does this card solve?" and "what role does it fill?"
- summary should explain WHY a deck plays this card, not just restate the oracle text
- For lands, always include "land" as a role plus any sub-role (color_fixing_land, utility_land)
- For creatures with tap abilities that produce mana, include "mana_dork"
- For artifacts that produce mana, include "mana_rock"
- power_level should reflect Commander format specifically

SEARCH_TERMS — include 4-6 terms mixing BOTH jargon AND plain English:
- Jargon: "sac outlet", "ETB trigger", "cantrip", "anthem", "hatebear"
- Plain English: "sacrifice for value", "when it enters", "draw a card cheap", "buff all creatures"
- Think: "what problem does this card solve?" from both expert AND beginner perspectives
- Do NOT include the card's own name

MULTI-ROLE: Tag ALL roles a card fills, not just the primary one.
- Solemn Simulacrum = ramp + card_draw + death_trigger
- Sakura-Tribe Elder = ramp + sacrifice_outlet
- Beast Within = removal_single + utility (hits any permanent)
If a card does two things, tag both. If it does three, tag all three."""


def _load_knowledge_base():
    """Load the knowledge base document."""
    kb_path = Path(os.path.dirname(os.path.abspath(__file__))) / "mtg_tagging_knowledge.md"
    if kb_path.exists():
        with open(kb_path) as f:
            return f.read()
    return ""


def _format_card_for_tagging(card):
    """Format a single card with rich context for AI tagging."""
    oracle = (card.get("oracle_text") or "")[:400]
    colors = ", ".join(card.get("color_identity", [])) or "Colorless"
    cmc = card.get("cmc", 0)
    keywords = ", ".join(card.get("keywords", []))

    if cmc <= 2:
        cmc_desc = "very cheap"
    elif cmc <= 3:
        cmc_desc = "cheap"
    elif cmc <= 5:
        cmc_desc = "mid-range cost"
    elif cmc <= 7:
        cmc_desc = "expensive"
    else:
        cmc_desc = "very expensive"

    parts = [
        f"Card: {card['name']} {card.get('mana_cost', '')} (CMC {cmc}, {cmc_desc})",
        f"Type: {card.get('type_line', '')}",
        f"Color Identity: {colors}",
    ]

    if oracle:
        parts.append(f"Oracle: {oracle}")
    if card.get("power") and card.get("toughness"):
        parts.append(f"Stats: {card['power']}/{card['toughness']}")
    if keywords:
        parts.append(f"Keywords: {keywords}")

    legalities = card.get("legalities", {})
    legal_formats = [f for f in ["commander", "modern", "standard", "pioneer"]
                     if legalities.get(f) == "legal"]
    if legal_formats:
        parts.append(f"Legal in: {', '.join(legal_formats)}")

    return "\n".join(parts)


def _validate_tags(tags, card_name):
    """Validate and fix AI-generated tags against allowed values."""
    fixed = dict(tags)

    if "roles" in fixed:
        valid_roles = [r for r in fixed["roles"] if r in ALLOWED_ROLES]
        invalid_roles = [r for r in fixed["roles"] if r not in ALLOWED_ROLES]
        if invalid_roles:
            role_fixes = {
                "removal": "removal_single", "board_wipe": "removal_board_wipe",
                "boardwipe": "removal_board_wipe", "draw": "card_draw",
                "counter": "counterspell", "sac_outlet": "sacrifice_outlet",
                "reanimation_spell": "reanimation", "graveyard_recursion": "recursion",
                "color_fixing": "mana_fixing", "pump_spell": "pump",
                "combat_damage": "evasion", "mana_acceleration": "ramp",
                "card_filtering": "card_selection", "token_production": "token_generator",
            }
            for invalid in invalid_roles:
                mapped = role_fixes.get(invalid)
                if mapped and mapped not in valid_roles:
                    valid_roles.append(mapped)
        fixed["roles"] = valid_roles if valid_roles else ["utility"]

    if "archetypes" in fixed:
        valid_archs = [a for a in fixed["archetypes"] if a in ALLOWED_ARCHETYPES]
        if not valid_archs:
            valid_archs = ["goodstuff"]
        fixed["archetypes"] = valid_archs

    if "power_level" in fixed:
        if fixed["power_level"] not in ALLOWED_POWER_LEVELS:
            fixed["power_level"] = "niche"

    if "search_terms" in fixed:
        name_lower = card_name.lower()
        fixed["search_terms"] = [
            t for t in fixed["search_terms"]
            if t.lower() != name_lower and name_lower not in t.lower()
        ]

    fixed["name"] = card_name
    return fixed


# ── Download ──────────────────────────────────────────

def download_cards():
    """Download unique cards from Scryfall bulk data."""
    if BULK_CACHE.exists():
        print(f"[DOWNLOAD] Loading cached cards from {BULK_CACHE}")
        with open(BULK_CACHE) as f:
            return json.load(f)

    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    print("[DOWNLOAD] Fetching Scryfall bulk data catalog...")
    resp = httpx.get("https://api.scryfall.com/bulk-data", headers=SCRYFALL_HEADERS, timeout=30)
    bulk_data = resp.json()

    oracle_url = None
    for item in bulk_data["data"]:
        if item["type"] == "oracle_cards":
            oracle_url = item["download_uri"]
            break

    if not oracle_url:
        raise RuntimeError("Could not find oracle_cards in Scryfall bulk data")

    print("[DOWNLOAD] Downloading oracle cards (~80MB)...")
    resp = httpx.get(oracle_url, headers=SCRYFALL_HEADERS, timeout=300)
    raw_cards = resp.json()
    print(f"[DOWNLOAD] Downloaded {len(raw_cards)} raw cards")

    cards = []
    seen_oracle_ids = set()

    for card in raw_cards:
        if card.get("layout") in ("token", "emblem", "art_series", "double_faced_token", "planar", "scheme", "vanguard"):
            continue
        if card.get("digital", False):
            continue

        oracle_id = card.get("oracle_id")
        if oracle_id and oracle_id in seen_oracle_ids:
            continue
        if oracle_id:
            seen_oracle_ids.add(oracle_id)

        oracle_text = card.get("oracle_text") or ""
        type_line = card.get("type_line", "")
        mana_cost = card.get("mana_cost", "")
        power = card.get("power")
        toughness = card.get("toughness")
        image_uris = card.get("image_uris")

        if card.get("card_faces"):
            faces = card["card_faces"]
            face_texts = []
            for face in faces:
                face_text = face.get("oracle_text", "")
                if face_text:
                    face_texts.append(f"[{face.get('name', '')}] {face_text}")
            oracle_text = " // ".join(face_texts) if face_texts else oracle_text
            if not type_line:
                type_line = " // ".join(f.get("type_line", "") for f in faces)
            if not mana_cost:
                mana_cost = faces[0].get("mana_cost", "")
            if not power and faces[0].get("power"):
                power = faces[0]["power"]
                toughness = faces[0].get("toughness")
            if not image_uris and faces[0].get("image_uris"):
                image_uris = faces[0]["image_uris"]

        cards.append({
            "scryfall_id": card["id"],
            "oracle_id": oracle_id,
            "name": card["name"],
            "type_line": type_line,
            "oracle_text": oracle_text,
            "mana_cost": mana_cost,
            "cmc": card.get("cmc", 0),
            "colors": card.get("colors", []),
            "color_identity": card.get("color_identity", []),
            "legalities": card.get("legalities", {}),
            "prices": card.get("prices", {}),
            "image_uris": image_uris or {},
            "power": power,
            "toughness": toughness,
            "rarity": card.get("rarity", ""),
            "set_code": card.get("set", ""),
            "keywords": card.get("keywords", []),
        })

    print(f"[DOWNLOAD] Filtered to {len(cards)} unique playable cards")
    with open(BULK_CACHE, "w") as f:
        json.dump(cards, f)
    return cards


# ── Step 1: PREPARE — Build and upload batch file ─────

def prepare_batch(cards):
    """Build JSONL batch file and upload to OpenAI."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    knowledge_base = _load_knowledge_base()
    system_content = TAGGING_SYSTEM_PROMPT
    if knowledge_base:
        system_content = knowledge_base + "\n\n---\n\nTAGGING INSTRUCTIONS:\n\n" + TAGGING_SYSTEM_PROMPT
        print(f"[PREPARE] Knowledge base loaded ({len(knowledge_base)} chars)")

    # Load existing tags to skip already-tagged cards
    existing_tags = {}
    if TAGS_CACHE.exists():
        with open(TAGS_CACHE) as f:
            for tag in json.load(f):
                existing_tags[tag["name"].lower()] = tag
        print(f"[PREPARE] {len(existing_tags)} cards already tagged, skipping those")

    cards_to_tag = [c for c in cards if c["name"].lower() not in existing_tags]
    print(f"[PREPARE] {len(cards_to_tag)} cards to tag")

    if not cards_to_tag:
        print("[PREPARE] All cards already tagged!")
        return

    # Build JSONL batch file
    batch_size = 25
    batch_count = 0

    with open(BATCH_FILE, "w") as f:
        for i in range(0, len(cards_to_tag), batch_size):
            batch = cards_to_tag[i:i + batch_size]
            card_texts = [_format_card_for_tagging(c) for c in batch]
            user_msg = "Generate strategic metadata for these cards:\n\n" + "\n---\n".join(card_texts)

            # Store card names in custom_id so we can match results back
            card_names = [c["name"] for c in batch]
            custom_id = f"batch_{i // batch_size}"

            request = {
                "custom_id": custom_id,
                "method": "POST",
                "url": "/v1/chat/completions",
                "body": {
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": system_content},
                        {"role": "user", "content": user_msg},
                    ],
                    "temperature": 0.2,
                    "max_tokens": 4000,
                },
            }

            f.write(json.dumps(request) + "\n")
            batch_count += 1

    print(f"[PREPARE] Created {batch_count} batch requests in {BATCH_FILE}")
    file_size_mb = BATCH_FILE.stat().st_size / (1024 * 1024)
    print(f"[PREPARE] File size: {file_size_mb:.1f} MB")

    # Upload file to OpenAI
    print("[PREPARE] Uploading batch file to OpenAI...")
    with open(BATCH_FILE, "rb") as f:
        uploaded = client.files.create(file=f, purpose="batch")

    print(f"[PREPARE] File uploaded: {uploaded.id}")

    # Create batch job
    print("[PREPARE] Creating batch job...")
    batch = client.batches.create(
        input_file_id=uploaded.id,
        endpoint="/v1/chat/completions",
        completion_window="24h",
        metadata={
            "description": "MTG card strategic tagging",
            "card_count": str(len(cards_to_tag)),
            "batch_count": str(batch_count),
        },
    )

    # Save batch ID for status checking
    with open(BATCH_ID_FILE, "w") as f:
        f.write(batch.id)

    print(f"[PREPARE] Batch job created: {batch.id}")
    print(f"[PREPARE] Status: {batch.status}")
    print(f"[PREPARE] Run 'python scripts/ingest_batch.py status' to check progress")

    # Also save the card-to-batch mapping for result parsing
    batch_map = {}
    for i in range(0, len(cards_to_tag), batch_size):
        batch = cards_to_tag[i:i + batch_size]
        batch_id = f"batch_{i // batch_size}"
        batch_map[batch_id] = [c["name"] for c in batch]

    with open(CACHE_DIR / "batch_map.json", "w") as f:
        json.dump(batch_map, f)


# ── Step 2: STATUS — Check batch progress ────────────

def check_status():
    """Check the status of the batch job."""
    if not BATCH_ID_FILE.exists():
        print("[STATUS] No batch job found. Run 'prepare' first.")
        return

    batch_id = BATCH_ID_FILE.read_text().strip()
    batch = client.batches.retrieve(batch_id)

    print(f"[STATUS] Batch ID: {batch.id}")
    print(f"[STATUS] Status: {batch.status}")
    print(f"[STATUS] Created: {batch.created_at}")

    if batch.request_counts:
        total = batch.request_counts.total
        completed = batch.request_counts.completed
        failed = batch.request_counts.failed
        print(f"[STATUS] Progress: {completed}/{total} completed, {failed} failed")

        if total > 0:
            pct = (completed / total) * 100
            print(f"[STATUS] {pct:.1f}% done")

    if batch.status == "completed":
        print(f"[STATUS] ✓ Batch complete! Run 'python scripts/ingest_batch.py complete' to process results")
    elif batch.status == "failed":
        print(f"[STATUS] ✗ Batch failed!")
        if batch.errors:
            for error in batch.errors.data:
                print(f"  Error: {error.message}")
    elif batch.status in ("validating", "in_progress", "finalizing"):
        print(f"[STATUS] Still processing... check again in a few minutes")
    elif batch.status == "expired":
        print(f"[STATUS] Batch expired (took longer than 24h)")


# ── Step 3: COMPLETE — Download results and store ─────

def complete_batch(cards):
    """Download batch results, parse tags, generate embeddings, store in DB."""
    if not BATCH_ID_FILE.exists():
        print("[COMPLETE] No batch job found. Run 'prepare' first.")
        return

    batch_id = BATCH_ID_FILE.read_text().strip()
    batch = client.batches.retrieve(batch_id)

    if batch.status != "completed":
        print(f"[COMPLETE] Batch not ready yet. Status: {batch.status}")
        print(f"[COMPLETE] Run 'status' to check progress")
        return

    # Download results
    print("[COMPLETE] Downloading batch results...")
    output_file_id = batch.output_file_id
    result_content = client.files.content(output_file_id)

    with open(BATCH_RESULTS_FILE, "wb") as f:
        f.write(result_content.content)

    # Load batch map
    batch_map = {}
    batch_map_file = CACHE_DIR / "batch_map.json"
    if batch_map_file.exists():
        with open(batch_map_file) as f:
            batch_map = json.load(f)

    # Load existing tags
    existing_tags = {}
    if TAGS_CACHE.exists():
        with open(TAGS_CACHE) as f:
            for tag in json.load(f):
                existing_tags[tag["name"].lower()] = tag

    # Parse results
    print("[COMPLETE] Parsing batch results...")
    new_tags = 0
    failures = 0

    with open(BATCH_RESULTS_FILE) as f:
        for line in f:
            result = json.loads(line)
            custom_id = result.get("custom_id", "")
            response_body = result.get("response", {}).get("body", {})

            if result.get("error"):
                print(f"  [ERROR] {custom_id}: {result['error']}")
                failures += 1
                continue

            # Extract content from response
            choices = response_body.get("choices", [])
            if not choices:
                failures += 1
                continue

            content = choices[0].get("message", {}).get("content", "")
            content = content.strip().replace("```json", "").replace("```", "").strip()

            # Parse JSON
            try:
                tags = json.loads(content)
            except json.JSONDecodeError:
                fixed = re.sub(r',\s*}', '}', content)
                fixed = re.sub(r',\s*]', ']', fixed)
                try:
                    tags = json.loads(fixed)
                except json.JSONDecodeError:
                    match = re.search(r'\[.*\]', fixed, re.DOTALL)
                    if match:
                        try:
                            tags = json.loads(match.group())
                        except:
                            failures += 1
                            continue
                    else:
                        failures += 1
                        continue

            # Get expected card names for this batch
            expected_names = batch_map.get(custom_id, [])
            batch_name_lookup = {n.lower(): n for n in expected_names}

            # Validate and store each tag
            for tag in tags:
                original_name = tag.get("name", "")
                matched_name = batch_name_lookup.get(original_name.lower(), original_name)
                validated = _validate_tags(tag, matched_name)
                existing_tags[matched_name.lower()] = validated
                new_tags += 1

    # Save all tags
    all_tags = list(existing_tags.values())
    with open(TAGS_CACHE, "w") as f:
        json.dump(all_tags, f)

    print(f"[COMPLETE] Parsed {new_tags} new tags, {failures} failures")
    print(f"[COMPLETE] Total tags: {len(all_tags)}")

    # Generate embeddings
    print(f"\n[EMBED] Generating embeddings for {len(cards)} cards...")
    tag_lookup = {t["name"].lower(): t for t in all_tags}

    from scripts.ingest_cards import build_embedding_text, generate_embeddings

    texts = [
        build_embedding_text(card, tag_lookup.get(card["name"].lower()))
        for card in cards
    ]
    embeddings = generate_embeddings(texts)

    # Store in database
    print(f"\n[STORE] Storing {len(cards)} cards in database...")
    db = SessionLocal()

    try:
        db.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        db.commit()
    except:
        db.rollback()

    # Clear existing cards
    db.execute(text("TRUNCATE cards"))
    db.commit()

    inserted = 0
    for i, card in enumerate(cards):
        tags = tag_lookup.get(card["name"].lower(), {})
        embedding = embeddings[i] if i < len(embeddings) else None

        db_card = Card(
            scryfall_id=card["scryfall_id"],
            oracle_id=card.get("oracle_id"),
            name=card["name"],
            type_line=card.get("type_line"),
            oracle_text=card.get("oracle_text"),
            mana_cost=card.get("mana_cost"),
            cmc=card.get("cmc"),
            colors=card.get("colors"),
            color_identity=card.get("color_identity"),
            legalities=card.get("legalities"),
            prices=card.get("prices"),
            image_uris=card.get("image_uris"),
            power=card.get("power"),
            toughness=card.get("toughness"),
            rarity=card.get("rarity"),
            set_code=card.get("set_code"),
            keywords=card.get("keywords"),
            roles=tags.get("roles"),
            archetypes=tags.get("archetypes"),
            search_terms=tags.get("search_terms"),
            synergies=tags.get("synergies"),
            power_level=tags.get("power_level"),
            strategic_summary=tags.get("summary"),
            embedding=embedding,
            updated_at=datetime.now(timezone.utc),
        )
        db.add(db_card)
        inserted += 1

        if inserted % 500 == 0:
            db.commit()
            print(f"[STORE] Progress: {inserted} inserted")

    db.commit()
    db.close()

    print(f"\n{'=' * 60}")
    print("Ingest complete!")
    print(f"  Cards: {len(cards)}")
    print(f"  Tags: {len(all_tags)}")
    print(f"  Embeddings: {len(embeddings)}")
    print(f"  Failures: {failures}")
    print("=" * 60)


# ── Main ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Batch ingest MTG cards")
    parser.add_argument("action", choices=["prepare", "status", "complete"],
                        help="prepare=upload batch, status=check progress, complete=download and store")
    parser.add_argument("--sample", type=int, help="Only process N cards (for testing)")
    args = parser.parse_args()

    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    if args.action == "prepare":
        cards = download_cards()
        if args.sample:
            cards = cards[:args.sample]
        prepare_batch(cards)

    elif args.action == "status":
        check_status()

    elif args.action == "complete":
        cards = download_cards()
        if args.sample:
            cards = cards[:args.sample]
        complete_batch(cards)


if __name__ == "__main__":
    main()