"""
MTG Card Vector Search Prototype — AI-Enriched Embeddings
Compares raw embeddings vs AI-tagged embeddings on a 50-card sample.

Usage:
  1. Set OPENAI_API_KEY environment variable
  2. python vector_test_enriched.py

Tests search quality with strategic tags added by GPT.
"""

import json
import os
import time
import pickle
from pathlib import Path

import httpx
import numpy as np
from openai import OpenAI

CACHE_DIR = Path("vector_cache")
CARDS_CACHE = CACHE_DIR / "cards.json"
ENRICHED_CACHE = CACHE_DIR / "enriched_tags.json"
ENRICHED_EMBEDDINGS_CACHE = CACHE_DIR / "enriched_embeddings.pkl"
RAW_EMBEDDINGS_CACHE = CACHE_DIR / "embeddings.pkl"

SCRYFALL_HEADERS = {
    "User-Agent": "MTGDeckIntelligence/1.0",
    "Accept": "application/json",
}

client = OpenAI()

# 50 well-known cards spanning different roles and archetypes
SAMPLE_CARDS = [
    "Sol Ring", "Command Tower", "Swords to Plowshares", "Cultivate",
    "Kodama's Reach", "Rhystic Study", "Cyclonic Rift", "Demonic Tutor",
    "Lightning Greaves", "Swiftfoot Boots", "Beast Within", "Chaos Warp",
    "Counterspell", "Path to Exile", "Skullclamp", "Smothering Tithe",
    "Arcane Signet", "Heroic Intervention", "Teferi's Protection",
    "Dockside Extortionist", "Mystic Remora", "Sylvan Library",
    "Phyrexian Arena", "Necropotence", "Viscera Seer", "Blood Artist",
    "Zulaport Cutthroat", "Grave Pact", "Dictate of Erebos",
    "Avenger of Zendikar", "Craterhoof Behemoth", "Torment of Hailfire",
    "Exsanguinate", "Reliquary Tower", "Thought Vessel", "Mind Stone",
    "Fellwar Stone", "Nature's Claim", "Return to Nature", "Generous Gift",
    "Vandalblast", "Toxic Deluge", "Wrath of God", "Blasphemous Act",
    "Eternal Witness", "Sun Titan", "Reanimate", "Animate Dead",
    "Notion Thief", "Narset, Parter of Veils",
]


def load_cards():
    """Load cards from cache."""
    if not CARDS_CACHE.exists():
        print("ERROR: Run vector_test.py first to download cards")
        exit(1)
    with open(CARDS_CACHE) as f:
        return json.load(f)


def find_sample_cards(all_cards):
    """Find our 50 sample cards in the full card list."""
    name_map = {c["name"].lower(): c for c in all_cards}
    sample = []
    missing = []
    for name in SAMPLE_CARDS:
        card = name_map.get(name.lower())
        if card:
            sample.append(card)
        else:
            missing.append(name)
    if missing:
        print(f"Warning: {len(missing)} cards not found: {missing[:5]}...")
    print(f"Found {len(sample)} / {len(SAMPLE_CARDS)} sample cards")
    return sample


def generate_ai_tags(sample_cards):
    """Generate strategic tags for sample cards using GPT."""
    if ENRICHED_CACHE.exists():
        print("Loading cached AI tags...")
        with open(ENRICHED_CACHE) as f:
            return json.load(f)

    print("Generating AI strategic tags for sample cards...")

    SYSTEM_PROMPT = """You are an expert Magic: The Gathering deck builder with deep knowledge of the Commander format.

For each card provided, generate strategic metadata that captures what experienced players know about this card — not just what the card text says, but HOW it's used and WHY decks play it.

Respond with ONLY a JSON array, no markdown backticks:
[
  {
    "name": "Card Name",
    "roles": ["role1", "role2"],
    "archetypes": ["archetype1", "archetype2"],
    "power_level": "format_staple|color_staple|archetype_staple|niche",
    "search_terms": ["term1", "term2", "term3"],
    "synergies": ["synergy1", "synergy2"],
    "summary": "One sentence capturing what experienced players know about this card."
  }
]

ROLES (use these consistently):
ramp, mana_fixing, mana_rock, mana_dork, card_draw, card_advantage, card_selection,
removal_single, removal_board_wipe, removal_exile, counterspell, protection, hexproof_enabler,
tutor, recursion, sacrifice_outlet, death_trigger, etb_trigger, finisher, win_condition,
combo_piece, stax, tax_effect, pillowfort, evasion, token_generator, anthem, lifegain,
lifegain_payoff, graveyard_fill, reanimation, reanimation_target, land_destruction,
artifact_hate, enchantment_hate, utility, equipment, aura

ARCHETYPES:
aristocrats, tokens, voltron, spellslinger, storm, reanimator, mill, control, aggro,
midrange, group_hug, group_slug, stax, tribal, landfall, enchantress, artifacts_matter,
equipment, blink, clone, theft, politics, combo, goodstuff, any_deck

SEARCH_TERMS should include what a player would TYPE when looking for this card's effect:
- Not the card name itself
- Think: "what problem does this card solve?" and "what would someone search to find this?"
- Examples: "cheap removal", "board wipe", "ramp spell", "draw engine", "sacrifice outlet",
  "protect my creatures", "steal opponents creatures", "graveyard hate"
"""

    # Batch in groups of 10
    all_tags = []
    batch_size = 10
    for i in range(0, len(sample_cards), batch_size):
        batch = sample_cards[i:i + batch_size]
        card_texts = []
        for c in batch:
            oracle = c.get("oracle_text", "") or ""
            card_texts.append(
                f"Card: {c['name']} {c.get('mana_cost', '')}\n"
                f"Type: {c.get('type_line', '')}\n"
                f"Oracle: {oracle[:300]}\n"
            )

        user_msg = "Generate strategic metadata for these cards:\n\n" + "\n---\n".join(card_texts)

        print(f"  Tagging batch {i // batch_size + 1}/{(len(sample_cards) + batch_size - 1) // batch_size}...")

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.2,
        )

        content = response.choices[0].message.content.strip()
        content = content.replace("```json", "").replace("```", "").strip()

        try:
            tags = json.loads(content)
            all_tags.extend(tags)
        except json.JSONDecodeError as e:
            print(f"  JSON parse error: {e}")
            # Try to fix common issues
            import re
            fixed = re.sub(r',\s*}', '}', content)
            fixed = re.sub(r',\s*]', ']', fixed)
            try:
                tags = json.loads(fixed)
                all_tags.extend(tags)
            except:
                print(f"  Skipping batch, could not parse")

        time.sleep(0.5)

    # Save cache
    CACHE_DIR.mkdir(exist_ok=True)
    with open(ENRICHED_CACHE, "w") as f:
        json.dump(all_tags, f, indent=2)

    print(f"Generated tags for {len(all_tags)} cards")
    return all_tags


def build_raw_text(card):
    """Original embedding text — just card data."""
    parts = [card["name"]]
    if card.get("type_line"):
        parts.append(card["type_line"])
    if card.get("oracle_text"):
        parts.append(card["oracle_text"])
    if card.get("power") and card.get("toughness"):
        parts.append(f"{card['power']}/{card['toughness']}")
    return ". ".join(parts)


def build_enriched_text(card, tags):
    """Enriched embedding text — card data + AI strategic tags."""
    parts = [card["name"]]
    if card.get("type_line"):
        parts.append(card["type_line"])
    if card.get("oracle_text"):
        parts.append(card["oracle_text"])
    if card.get("power") and card.get("toughness"):
        parts.append(f"{card['power']}/{card['toughness']}")

    # Add strategic context from AI tags
    if tags:
        if tags.get("roles"):
            parts.append(f"Roles: {', '.join(tags['roles'])}")
        if tags.get("archetypes"):
            parts.append(f"Archetypes: {', '.join(tags['archetypes'])}")
        if tags.get("search_terms"):
            parts.append(f"Players search for: {', '.join(tags['search_terms'])}")
        if tags.get("synergies"):
            parts.append(f"Synergies: {', '.join(tags['synergies'])}")
        if tags.get("summary"):
            parts.append(tags["summary"])
        if tags.get("power_level"):
            parts.append(f"Power level: {tags['power_level']}")

    return ". ".join(parts)


def generate_comparison_embeddings(sample_cards, ai_tags):
    """Generate both raw and enriched embeddings for comparison."""
    if ENRICHED_EMBEDDINGS_CACHE.exists():
        print("Loading cached enriched embeddings...")
        with open(ENRICHED_EMBEDDINGS_CACHE, "rb") as f:
            return pickle.load(f)

    # Build tag lookup
    tag_lookup = {t["name"].lower(): t for t in ai_tags}

    raw_texts = [build_raw_text(c) for c in sample_cards]
    enriched_texts = [build_enriched_text(c, tag_lookup.get(c["name"].lower())) for c in sample_cards]

    print("\n--- Example comparison ---")
    print(f"RAW: {raw_texts[0][:200]}...")
    print(f"ENRICHED: {enriched_texts[0][:300]}...")
    print("---\n")

    print("Embedding raw texts...")
    raw_response = client.embeddings.create(model="text-embedding-3-small", input=raw_texts)
    raw_embeddings = np.array([item.embedding for item in raw_response.data], dtype=np.float32)

    print("Embedding enriched texts...")
    enriched_response = client.embeddings.create(model="text-embedding-3-small", input=enriched_texts)
    enriched_embeddings = np.array([item.embedding for item in enriched_response.data], dtype=np.float32)

    data = {
        "raw": raw_embeddings,
        "enriched": enriched_embeddings,
    }

    CACHE_DIR.mkdir(exist_ok=True)
    with open(ENRICHED_EMBEDDINGS_CACHE, "wb") as f:
        pickle.dump(data, f)

    return data


def search_compare(query, sample_cards, raw_embeddings, enriched_embeddings, top_k=5):
    """Search both raw and enriched embeddings and compare results."""
    response = client.embeddings.create(model="text-embedding-3-small", input=query)
    query_emb = np.array(response.data[0].embedding, dtype=np.float32)

    # Raw search
    raw_norms = np.linalg.norm(raw_embeddings, axis=1) * np.linalg.norm(query_emb)
    raw_sims = np.dot(raw_embeddings, query_emb) / raw_norms
    raw_top = np.argsort(raw_sims)[::-1][:top_k]

    # Enriched search
    enr_norms = np.linalg.norm(enriched_embeddings, axis=1) * np.linalg.norm(query_emb)
    enr_sims = np.dot(enriched_embeddings, query_emb) / enr_norms
    enr_top = np.argsort(enr_sims)[::-1][:top_k]

    print(f"\n{'=' * 60}")
    print(f"Query: '{query}'")
    print(f"{'=' * 60}")

    print(f"\n  RAW EMBEDDINGS (card text only):")
    print(f"  {'-' * 45}")
    for rank, idx in enumerate(raw_top, 1):
        c = sample_cards[idx]
        print(f"  {rank}. {c['name']} ({c.get('mana_cost', '')}) — sim: {raw_sims[idx]:.3f}")
        oracle = (c.get("oracle_text") or "")[:100]
        print(f"     {oracle}")

    print(f"\n  ENRICHED EMBEDDINGS (card text + AI tags):")
    print(f"  {'-' * 45}")
    for rank, idx in enumerate(enr_top, 1):
        c = sample_cards[idx]
        print(f"  {rank}. {c['name']} ({c.get('mana_cost', '')}) — sim: {enr_sims[idx]:.3f}")
        oracle = (c.get("oracle_text") or "")[:100]
        print(f"     {oracle}")

    # Highlight differences
    raw_names = {sample_cards[i]["name"] for i in raw_top}
    enr_names = {sample_cards[i]["name"] for i in enr_top}
    only_raw = raw_names - enr_names
    only_enriched = enr_names - raw_names
    if only_raw or only_enriched:
        print(f"\n  DIFFERENCES:")
        if only_enriched:
            print(f"  + Enriched found: {', '.join(only_enriched)}")
        if only_raw:
            print(f"  - Raw had (enriched dropped): {', '.join(only_raw)}")


def interactive(sample_cards, raw_embeddings, enriched_embeddings):
    """Interactive comparison search."""
    print("\n" + "=" * 60)
    print("MTG Vector Search — RAW vs ENRICHED Comparison")
    print(f"Testing on {len(sample_cards)} well-known cards")
    print("=" * 60)
    print("Type a search query to compare raw vs enriched results.")
    print("Type 'auto' to run preset test queries.")
    print("Type 'tags' to see what AI generated for a card.")
    print("Type 'quit' to exit.")
    print("=" * 60)

    while True:
        query = input("\nSearch: ").strip()
        if not query:
            continue
        if query.lower() == "quit":
            break

        if query.lower() == "auto":
            test_queries = [
                "ramp spells that accelerate mana",
                "card draw engines",
                "cheap instant speed removal",
                "protect my creatures from removal",
                "sacrifice outlets for aristocrats",
                "cards that punish opponents for drawing",
                "finishers that end the game",
                "graveyard recursion",
                "mana rocks",
                "board wipes that destroy everything",
            ]
            for q in test_queries:
                search_compare(q, sample_cards, raw_embeddings, enriched_embeddings)
            continue

        if query.lower().startswith("tags "):
            card_name = query[5:].strip().lower()
            if ENRICHED_CACHE.exists():
                with open(ENRICHED_CACHE) as f:
                    tags = json.load(f)
                found = next((t for t in tags if t["name"].lower() == card_name), None)
                if found:
                    print(json.dumps(found, indent=2))
                else:
                    print(f"No tags found for '{card_name}'")
            continue

        search_compare(query, sample_cards, raw_embeddings, enriched_embeddings)


if __name__ == "__main__":
    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: Set OPENAI_API_KEY environment variable")
        exit(1)

    all_cards = load_cards()
    sample = find_sample_cards(all_cards)
    ai_tags = generate_ai_tags(sample)
    embeddings = generate_comparison_embeddings(sample, ai_tags)

    interactive(sample, embeddings["raw"], embeddings["enriched"])