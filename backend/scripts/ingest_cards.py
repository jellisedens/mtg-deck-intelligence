"""
MTG Card Ingest Script (v2)
Downloads all cards from Scryfall, generates AI strategic tags,
creates embeddings, and stores everything in the cards table.

Improvements over v1:
1. Better deduplication — keeps most recent printing per oracle_id
2. Double-faced card handling — embeds both faces as one entry
3. Enhanced tagging prompt — includes keywords, CMC, color context
4. Structured embedding text — consistent format for better similarity
5. Batch error recovery — tracks tagged cards, retries failures
6. AI output validation — validates roles/archetypes against allowed lists

Usage:
  docker exec mtg-backend python scripts/ingest_cards.py

Options:
  --skip-tags     Skip AI tagging (just download + embed raw text)
  --skip-embed    Skip embedding generation (just download + tag)
  --sample N      Only process N cards (for testing)
  --resume        Resume from where we left off (skip already-ingested cards)

First run: ~30 min, ~$5 in OpenAI costs (tagging + embedding)
Subsequent runs with --resume: only processes new cards
"""

import os
import sys
import json
import time
import re
import argparse
from datetime import datetime, timezone
from pathlib import Path

# Add parent directory to path so we can import backend modules
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
FAILED_CACHE = CACHE_DIR / "failed_batches.json"

client = OpenAI()

# ── Allowed values for validation ─────────────────────

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


# ── Step 1: Download and deduplicate cards ────────────

def download_cards(sample_size=None):
    """Download unique cards from Scryfall bulk data with smart deduplication."""
    if BULK_CACHE.exists():
        print(f"[DOWNLOAD] Loading cached cards from {BULK_CACHE}")
        with open(BULK_CACHE) as f:
            cards = json.load(f)
        if sample_size:
            cards = cards[:sample_size]
        print(f"[DOWNLOAD] {len(cards)} cards loaded")
        return cards

    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    print("[DOWNLOAD] Fetching Scryfall bulk data catalog...")
    resp = httpx.get(
        "https://api.scryfall.com/bulk-data",
        headers=SCRYFALL_HEADERS,
        timeout=30,
    )
    bulk_data = resp.json()

    # Use default_cards for most complete data (includes all printings)
    oracle_url = None
    for item in bulk_data["data"]:
        if item["type"] == "oracle_cards":
            oracle_url = item["download_uri"]
            break

    if not oracle_url:
        raise RuntimeError("Could not find oracle_cards in Scryfall bulk data")

    print(f"[DOWNLOAD] Downloading oracle cards (~80MB)...")
    resp = httpx.get(oracle_url, headers=SCRYFALL_HEADERS, timeout=300)
    raw_cards = resp.json()
    print(f"[DOWNLOAD] Downloaded {len(raw_cards)} raw cards")

    # Filter and normalize with smart deduplication
    # oracle_cards already gives us one per oracle_id, but we still need to clean
    cards = []
    seen_oracle_ids = set()

    for card in raw_cards:
        # Skip non-playable layouts
        if card.get("layout") in (
            "token", "emblem", "art_series", "double_faced_token",
            "planar", "scheme", "vanguard",
        ):
            continue

        # Skip digital-only
        if card.get("digital", False):
            continue

        # Deduplicate by oracle_id (prefer first seen in oracle_cards)
        oracle_id = card.get("oracle_id")
        if oracle_id and oracle_id in seen_oracle_ids:
            continue
        if oracle_id:
            seen_oracle_ids.add(oracle_id)

        # ── Handle double-faced cards ──
        oracle_text = card.get("oracle_text") or ""
        type_line = card.get("type_line", "")
        mana_cost = card.get("mana_cost", "")
        power = card.get("power")
        toughness = card.get("toughness")
        image_uris = card.get("image_uris")

        if card.get("card_faces"):
            faces = card["card_faces"]
            # Combine oracle text from all faces
            face_texts = []
            for face in faces:
                face_text = face.get("oracle_text", "")
                if face_text:
                    face_texts.append(f"[{face.get('name', '')}] {face_text}")
            oracle_text = " // ".join(face_texts) if face_texts else oracle_text

            # Use front face for type/cost if not on main card
            if not type_line:
                type_line = " // ".join(f.get("type_line", "") for f in faces)
            if not mana_cost:
                mana_cost = faces[0].get("mana_cost", "")
            if not power and faces[0].get("power"):
                power = faces[0]["power"]
                toughness = faces[0].get("toughness")
            if not image_uris and faces[0].get("image_uris"):
                image_uris = faces[0]["image_uris"]

        # Build normalized card entry
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

    if sample_size:
        cards = cards[:sample_size]

    return cards


# ── Step 2: AI Strategic Tagging ──────────────────────

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

NEVER use roles not in the provided list. Do NOT invent roles like "creature", "scalable threat", "beater", "blocker" — use the closest match from the allowed list (usually "utility" or "finisher").

A card is ONLY "ramp" if it literally adds mana or puts lands onto the battlefield. Having "ramp" in the card name does NOT make it ramp. Greenbelt Rampager is "utility", NOT "ramp" — it produces no mana and fetches no lands.

MULTI-ROLE: Tag ALL roles a card fills, not just the primary one.
- Solemn Simulacrum = ramp + card_draw + death_trigger
- Sakura-Tribe Elder = ramp + sacrifice_outlet
- Beast Within = removal_single + utility (hits any permanent)
If a card does two things, tag both. If it does three, tag all three."""


def _format_card_for_tagging(card):
    """Format a single card with rich context for AI tagging."""
    oracle = (card.get("oracle_text") or "")[:400]
    colors = ", ".join(card.get("color_identity", [])) or "Colorless"
    cmc = card.get("cmc", 0)
    keywords = ", ".join(card.get("keywords", []))

    # CMC context
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

    # Add legality context
    legalities = card.get("legalities", {})
    legal_formats = [f for f in ["commander", "modern", "standard", "pioneer"]
                     if legalities.get(f) == "legal"]
    if legal_formats:
        parts.append(f"Legal in: {', '.join(legal_formats)}")

    return "\n".join(parts)


def _validate_tags(tags, card_name):
    """Validate and fix AI-generated tags against allowed values."""
    fixed = dict(tags)

    # Validate roles
    if "roles" in fixed:
        valid_roles = [r for r in fixed["roles"] if r in ALLOWED_ROLES]
        invalid_roles = [r for r in fixed["roles"] if r not in ALLOWED_ROLES]
        if invalid_roles:
            # Try to map common misspellings/alternatives
            role_fixes = {
                "removal": "removal_single",
                "board_wipe": "removal_board_wipe",
                "boardwipe": "removal_board_wipe",
                "draw": "card_draw",
                "counter": "counterspell",
                "sac_outlet": "sacrifice_outlet",
                "reanimation_spell": "reanimation",
                "graveyard_recursion": "recursion",
                "color_fixing": "mana_fixing",
                "pump_spell": "pump",
                "combat_damage": "evasion",
                "mana_acceleration": "ramp",
                "card_filtering": "card_selection",
                "token_production": "token_generator",
                "ETB_trigger": "etb_trigger",
                "ETB": "etb_trigger",
            }
            for invalid in invalid_roles:
                mapped = role_fixes.get(invalid)
                if mapped and mapped not in valid_roles:
                    valid_roles.append(mapped)

        fixed["roles"] = valid_roles if valid_roles else ["utility"]

    # Validate archetypes
    if "archetypes" in fixed:
        valid_archs = [a for a in fixed["archetypes"] if a in ALLOWED_ARCHETYPES]
        if not valid_archs:
            valid_archs = ["goodstuff"]
        fixed["archetypes"] = valid_archs

    # Validate power_level
    if "power_level" in fixed:
        if fixed["power_level"] not in ALLOWED_POWER_LEVELS:
            fixed["power_level"] = "niche"

    # Ensure search_terms don't include the card name
    if "search_terms" in fixed:
        name_lower = card_name.lower()
        fixed["search_terms"] = [
            t for t in fixed["search_terms"]
            if t.lower() != name_lower and name_lower not in t.lower()
        ]

    # Ensure name matches
    fixed["name"] = card_name

    return fixed


def generate_ai_tags(cards, resume_from=None):
    """Generate AI strategic tags for all cards with error recovery."""
    # Load knowledge base
    knowledge_path = Path(os.path.dirname(os.path.abspath(__file__))) / "mtg_tagging_knowledge.md"
    knowledge_context = ""
    if knowledge_path.exists():
        with open(knowledge_path) as f:
            knowledge_context = f.read()
        print(f"[TAGS] Loaded knowledge base ({len(knowledge_context)} chars)")
    else:
        print("[TAGS] No knowledge base found, using base prompt only")

    system_content = TAGGING_SYSTEM_PROMPT
    if knowledge_context:
        system_content = knowledge_context + "\n\n---\n\nTAGGING INSTRUCTIONS:\n\n" + TAGGING_SYSTEM_PROMPT

    # Load existing tags if resuming
    existing_tags = {}
    if TAGS_CACHE.exists():
        with open(TAGS_CACHE) as f:
            for tag in json.load(f):
                existing_tags[tag["name"].lower()] = tag

    # Load failed batches for retry
    failed_cards = set()
    if FAILED_CACHE.exists():
        with open(FAILED_CACHE) as f:
            failed_cards = set(json.load(f))
        print(f"[TAGS] {len(failed_cards)} previously failed cards to retry")

    # Filter out already-tagged cards (unless they failed before)
    cards_to_tag = []
    for c in cards:
        name_lower = c["name"].lower()
        if name_lower in existing_tags and name_lower not in failed_cards:
            continue
        cards_to_tag.append(c)

    if not cards_to_tag:
        print("[TAGS] All cards already tagged")
        return list(existing_tags.values())

    print(f"[TAGS] {len(existing_tags)} already tagged, {len(cards_to_tag)} remaining")

    all_tags = list(existing_tags.values())
    batch_size = 25
    total_batches = (len(cards_to_tag) + batch_size - 1) // batch_size
    new_failures = []

    print(f"[TAGS] Tagging {len(cards_to_tag)} cards in {total_batches} batches (10 parallel)...")

    from concurrent.futures import ThreadPoolExecutor, as_completed

    def _process_batch(batch_info):
        """Process a single batch — thread-safe."""
        batch_num, batch = batch_info
        card_texts = [_format_card_for_tagging(c) for c in batch]
        user_msg = "Generate strategic metadata for these cards:\n\n" + "\n---\n".join(card_texts)

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_content},
                    {"role": "user", "content": user_msg},
                ],
                temperature=0.2,
                max_tokens=4000,
            )

            content = response.choices[0].message.content.strip()
            content = content.replace("```json", "").replace("```", "").strip()

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
                        tags = json.loads(match.group())
                    else:
                        raise

            batch_name_lookup = {c["name"].lower(): c["name"] for c in batch}
            validated_tags = []
            for tag in tags:
                original_name = tag.get("name", "")
                matched_name = batch_name_lookup.get(original_name.lower(), original_name)
                validated = _validate_tags(tag, matched_name)
                validated_tags.append(validated)

            tagged_names = {t["name"].lower() for t in tags}
            batch_failures = [c["name"] for c in batch if c["name"].lower() not in tagged_names]

            return batch_num, validated_tags, batch_failures

        except Exception as e:
            return batch_num, [], [c["name"] for c in batch]

    # Build all batch jobs
    batch_jobs = []
    for i in range(0, len(cards_to_tag), batch_size):
        batch = cards_to_tag[i:i + batch_size]
        batch_num = i // batch_size + 1
        batch_jobs.append((batch_num, batch))

    # Execute in parallel
    completed_count = 0
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(_process_batch, job): job for job in batch_jobs}

        for future in as_completed(futures):
            batch_num, validated_tags, batch_failures = future.result()
            completed_count += 1

            for tag in validated_tags:
                all_tags.append(tag)
                existing_tags[tag["name"].lower()] = tag

            new_failures.extend(batch_failures)

            # Progress + save every 50 completions
            if completed_count % 50 == 0 or completed_count == total_batches:
                print(f"[TAGS] {completed_count}/{total_batches} batches done — {len(all_tags)} tags, {len(new_failures)} failures")
                CACHE_DIR.mkdir(parents=True, exist_ok=True)
                with open(TAGS_CACHE, "w") as f:
                    json.dump(all_tags, f)
                if new_failures:
                    with open(FAILED_CACHE, "w") as f:
                        json.dump(new_failures, f)

    # Final save
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with open(TAGS_CACHE, "w") as f:
        json.dump(all_tags, f)

    if new_failures:
        with open(FAILED_CACHE, "w") as f:
            json.dump(new_failures, f)
        print(f"[TAGS] {len(new_failures)} cards failed — run with --resume to retry")
    else:
        # Clear failures cache
        if FAILED_CACHE.exists():
            FAILED_CACHE.unlink()

    print(f"[TAGS] Generated {len(all_tags)} total tags")
    return all_tags


# ── Step 3: Generate Embeddings ───────────────────────

def build_embedding_text(card, tags=None):
    """Build structured enriched text for embedding."""
    parts = []

    # Structured header
    parts.append(f"Name: {card['name']}")

    cost = card.get("mana_cost", "")
    cmc = card.get("cmc", 0)
    if cost:
        parts.append(f"Cost: {cost} (CMC {cmc})")
    elif cmc:
        parts.append(f"CMC: {cmc}")

    if card.get("type_line"):
        parts.append(f"Type: {card['type_line']}")

    colors = card.get("color_identity", [])
    if colors:
        color_names = {"W": "White", "U": "Blue", "B": "Black", "R": "Red", "G": "Green"}
        parts.append(f"Colors: {', '.join(color_names.get(c, c) for c in colors)}")
    else:
        parts.append("Colors: Colorless")

    if card.get("oracle_text"):
        parts.append(f"Text: {card['oracle_text']}")

    if card.get("power") and card.get("toughness"):
        parts.append(f"Stats: {card['power']}/{card['toughness']}")

    keywords = card.get("keywords", [])
    if keywords:
        parts.append(f"Keywords: {', '.join(keywords)}")

    # Strategic context from AI tags
    if tags:
        if tags.get("roles"):
            role_display = [r.replace("_", " ") for r in tags["roles"]]
            parts.append(f"Roles: {', '.join(role_display)}")
        if tags.get("archetypes"):
            arch_display = [a.replace("_", " ") for a in tags["archetypes"]]
            parts.append(f"Archetypes: {', '.join(arch_display)}")
        if tags.get("search_terms"):
            parts.append(f"Players search for: {', '.join(tags['search_terms'])}")
        if tags.get("synergies"):
            parts.append(f"Synergies: {', '.join(tags['synergies'])}")
        if tags.get("summary"):
            parts.append(f"Strategy: {tags['summary']}")
        if tags.get("power_level"):
            parts.append(f"Power level: {tags['power_level'].replace('_', ' ')}")

    return "\n".join(parts)


def generate_embeddings(texts, batch_size=1000):
    """Generate embeddings for a list of texts."""
    all_embeddings = []

    total_batches = (len(texts) + batch_size - 1) // batch_size
    print(f"[EMBED] Generating embeddings for {len(texts)} cards in {total_batches} batches...")

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        batch_num = i // batch_size + 1

        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=batch,
        )

        for item in response.data:
            all_embeddings.append(item.embedding)

        print(f"[EMBED] Batch {batch_num}/{total_batches}")
        time.sleep(0.5)

    return all_embeddings


# ── Step 4: Store in Database ─────────────────────────

def store_cards(cards, tags_list, embeddings, resume=False):
    """Insert or update cards in the database."""
    db = SessionLocal()

    # Build tag lookup
    tag_lookup = {}
    for tag in tags_list:
        tag_lookup[tag["name"].lower()] = tag

    # Get existing scryfall_ids if resuming
    existing_ids = set()
    if resume:
        result = db.execute(text("SELECT scryfall_id FROM cards"))
        existing_ids = {row[0] for row in result}
        print(f"[STORE] {len(existing_ids)} cards already in database")

    inserted = 0
    updated = 0

    for i, card in enumerate(cards):
        tags = tag_lookup.get(card["name"].lower(), {})
        embedding = embeddings[i] if i < len(embeddings) else None

        if card["scryfall_id"] in existing_ids:
            # Update existing — refresh prices and legalities
            db.query(Card).filter(Card.scryfall_id == card["scryfall_id"]).update({
                "prices": card.get("prices"),
                "legalities": card.get("legalities"),
                "updated_at": datetime.now(timezone.utc),
            })
            updated += 1
        else:
            # Insert new
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

        # Commit in batches
        if (inserted + updated) % 500 == 0:
            db.commit()
            if (inserted + updated) % 2000 == 0:
                print(f"[STORE] Progress: {inserted} inserted, {updated} updated")

    db.commit()
    db.close()
    print(f"[STORE] Done: {inserted} inserted, {updated} updated")


# ── Main ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Ingest MTG cards into vector database")
    parser.add_argument("--skip-tags", action="store_true", help="Skip AI tagging")
    parser.add_argument("--skip-embed", action="store_true", help="Skip embedding generation")
    parser.add_argument("--sample", type=int, help="Only process N cards")
    parser.add_argument("--resume", action="store_true", help="Resume from previous run")
    args = parser.parse_args()

    print("=" * 60)
    print("MTG Card Ingest Pipeline v2")
    print("=" * 60)

    # Ensure vector extension exists
    db = SessionLocal()
    try:
        db.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        db.commit()
    except Exception as e:
        print(f"[WARN] Could not create vector extension: {e}")
        db.rollback()
    db.close()

    # Step 1: Download
    cards = download_cards(sample_size=args.sample)
    print(f"\n{'=' * 60}")

    # Step 2: AI Tags
    if args.skip_tags:
        print("[TAGS] Skipping AI tagging")
        tags = []
    else:
        tags = generate_ai_tags(cards, resume_from=args.resume)
    print(f"\n{'=' * 60}")

    # Step 3: Embeddings
    if args.skip_embed:
        print("[EMBED] Skipping embedding generation")
        embeddings = []
    else:
        tag_lookup = {t["name"].lower(): t for t in tags}
        texts = [
            build_embedding_text(card, tag_lookup.get(card["name"].lower()))
            for card in cards
        ]
        embeddings = generate_embeddings(texts)
    print(f"\n{'=' * 60}")

    # Step 4: Store
    store_cards(cards, tags, embeddings, resume=args.resume)

    print(f"\n{'=' * 60}")
    print("Ingest complete!")
    print(f"  Cards: {len(cards)}")
    print(f"  Tags: {len(tags)}")
    print(f"  Embeddings: {len(embeddings)}")
    if FAILED_CACHE.exists():
        with open(FAILED_CACHE) as f:
            failures = json.load(f)
        print(f"  Failed: {len(failures)} (run with --resume to retry)")
    print("=" * 60)


if __name__ == "__main__":
    main()