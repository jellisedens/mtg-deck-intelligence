"""
MTG Card Vector Search Prototype
Tests semantic card search using OpenAI embeddings + numpy cosine similarity.
No database needed — everything in memory.

Usage:
  1. Set OPENAI_API_KEY environment variable
  2. python vector_test.py

First run downloads cards from Scryfall and generates embeddings (~5 min).
Subsequent runs use cached data.
"""

import json
import os
import time
import pickle
from pathlib import Path

import httpx
import numpy as np
from openai import OpenAI

# Config
CACHE_DIR = Path("vector_cache")
CARDS_CACHE = CACHE_DIR / "cards.json"
EMBEDDINGS_CACHE = CACHE_DIR / "embeddings.pkl"
SCRYFALL_HEADERS = {
    "User-Agent": "MTGDeckIntelligence/1.0",
    "Accept": "application/json",
}

client = OpenAI()


def download_cards():
    """Download unique cards from Scryfall bulk data."""
    if CARDS_CACHE.exists():
        print(f"Loading cached cards from {CARDS_CACHE}")
        with open(CARDS_CACHE) as f:
            return json.load(f)

    CACHE_DIR.mkdir(exist_ok=True)

    print("Fetching Scryfall bulk data catalog...")
    resp = httpx.get("https://api.scryfall.com/bulk-data", headers=SCRYFALL_HEADERS, timeout=30)
    bulk_data = resp.json()

    # Find the "oracle_cards" dataset — unique cards only
    oracle_download = None
    for item in bulk_data["data"]:
        if item["type"] == "oracle_cards":
            oracle_download = item["download_uri"]
            break

    if not oracle_download:
        raise RuntimeError("Could not find oracle_cards bulk data")

    print(f"Downloading oracle cards (~30MB)...")
    resp = httpx.get(oracle_download, headers=SCRYFALL_HEADERS, timeout=120)
    all_cards = resp.json()

    # Filter to cards legal in commander with oracle text
    cards = []
    for card in all_cards:
        # Skip tokens, emblems, etc.
        if card.get("layout") in ("token", "emblem", "art_series", "double_faced_token"):
            continue
        # Must have oracle text
        oracle = card.get("oracle_text") or ""
        if card.get("card_faces"):
            oracle = " // ".join(f.get("oracle_text", "") for f in card["card_faces"])
        if not oracle and "Land" not in card.get("type_line", ""):
            continue

        cards.append({
            "id": card["id"],
            "name": card["name"],
            "type_line": card.get("type_line", ""),
            "oracle_text": oracle,
            "mana_cost": card.get("mana_cost", ""),
            "cmc": card.get("cmc", 0),
            "colors": card.get("colors", []),
            "color_identity": card.get("color_identity", []),
            "legalities": card.get("legalities", {}),
            "rarity": card.get("rarity", ""),
            "power": card.get("power"),
            "toughness": card.get("toughness"),
            "prices": card.get("prices", {}),
            "image_uris": card.get("image_uris", {}),
        })

    print(f"Filtered to {len(cards)} unique cards")

    with open(CARDS_CACHE, "w") as f:
        json.dump(cards, f)

    return cards


def build_embedding_text(card):
    """Build the text to embed for a card."""
    parts = [card["name"]]
    if card["type_line"]:
        parts.append(card["type_line"])
    if card["oracle_text"]:
        parts.append(card["oracle_text"])
    if card["power"] and card["toughness"]:
        parts.append(f"{card['power']}/{card['toughness']}")
    return ". ".join(parts)


def generate_embeddings(cards):
    """Generate embeddings for all cards using OpenAI."""
    if EMBEDDINGS_CACHE.exists():
        print(f"Loading cached embeddings from {EMBEDDINGS_CACHE}")
        with open(EMBEDDINGS_CACHE, "rb") as f:
            return pickle.load(f)

    print(f"Generating embeddings for {len(cards)} cards...")
    texts = [build_embedding_text(c) for c in cards]

    # Batch in chunks of 2048 (API limit)
    all_embeddings = []
    batch_size = 2048
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        print(f"  Embedding batch {i // batch_size + 1}/{(len(texts) + batch_size - 1) // batch_size} ({len(batch)} cards)...")
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=batch,
        )
        for item in response.data:
            all_embeddings.append(item.embedding)
        time.sleep(0.5)  # Rate limit courtesy

    embeddings = np.array(all_embeddings, dtype=np.float32)
    print(f"Embeddings shape: {embeddings.shape}")

    CACHE_DIR.mkdir(exist_ok=True)
    with open(EMBEDDINGS_CACHE, "wb") as f:
        pickle.dump(embeddings, f)

    return embeddings


def search(query, cards, embeddings, top_k=10, color_filter=None, format_filter=None):
    """Search for cards by semantic similarity."""
    # Embed the query
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=query,
    )
    query_embedding = np.array(response.data[0].embedding, dtype=np.float32)

    # Cosine similarity
    norms = np.linalg.norm(embeddings, axis=1) * np.linalg.norm(query_embedding)
    similarities = np.dot(embeddings, query_embedding) / norms

    # Apply filters
    mask = np.ones(len(cards), dtype=bool)
    if color_filter:
        for i, card in enumerate(cards):
            ci = set(card["color_identity"])
            allowed = set(color_filter)
            if not ci.issubset(allowed):
                mask[i] = False

    if format_filter:
        for i, card in enumerate(cards):
            if card["legalities"].get(format_filter) != "legal":
                mask[i] = False

    # Zero out filtered cards
    filtered_sims = similarities * mask

    # Top K
    top_indices = np.argsort(filtered_sims)[::-1][:top_k]

    results = []
    for idx in top_indices:
        card = cards[idx]
        results.append({
            "name": card["name"],
            "type_line": card["type_line"],
            "oracle_text": card["oracle_text"][:150],
            "mana_cost": card["mana_cost"],
            "colors": card["color_identity"],
            "similarity": float(filtered_sims[idx]),
            "price": card["prices"].get("usd", "?"),
        })

    return results


def interactive_search(cards, embeddings):
    """Interactive search loop."""
    print("\n" + "=" * 60)
    print("MTG Vector Search Prototype")
    print("=" * 60)
    print("Search for cards by concept, mechanic, or description.")
    print("Examples:")
    print("  - 'cards that punish opponents for drawing'")
    print("  - 'cheap removal that exiles'")
    print("  - 'ramp spells that put lands on the battlefield'")
    print("  - 'creatures that get bigger when other creatures die'")
    print("")
    print("Commands:")
    print("  color:BG  — filter to color identity (e.g., BG, WUR)")
    print("  format:commander — filter to format legality")
    print("  quit — exit")
    print("=" * 60)

    color_filter = None
    format_filter = "commander"  # Default to commander

    while True:
        print(f"\n[filters: colors={color_filter or 'any'}, format={format_filter or 'any'}]")
        query = input("Search: ").strip()

        if not query:
            continue
        if query.lower() == "quit":
            break

        # Parse commands
        if query.startswith("color:"):
            color_filter = list(query[6:].upper()) if query[6:] else None
            print(f"Color filter set to: {color_filter}")
            continue
        if query.startswith("format:"):
            format_filter = query[7:] if query[7:] else None
            print(f"Format filter set to: {format_filter}")
            continue

        results = search(query, cards, embeddings, top_k=10,
                        color_filter=color_filter, format_filter=format_filter)

        print(f"\nTop 10 results for: '{query}'")
        print("-" * 50)
        for i, r in enumerate(results, 1):
            price_str = f"${r['price']}" if r['price'] and r['price'] != '?' else "no price"
            print(f"{i:2}. {r['name']} ({r['mana_cost']}) — {r['type_line']}")
            print(f"    {r['oracle_text']}")
            print(f"    colors: {','.join(r['colors']) or 'C'}  |  sim: {r['similarity']:.3f}  |  {price_str}")
            print()


if __name__ == "__main__":
    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: Set OPENAI_API_KEY environment variable")
        print("  $env:OPENAI_API_KEY = 'sk-...'")
        exit(1)

    cards = download_cards()
    embeddings = generate_embeddings(cards)
    interactive_search(cards, embeddings)