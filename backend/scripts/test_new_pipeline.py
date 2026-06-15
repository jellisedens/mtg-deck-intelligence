import sys
sys.path.insert(0, "/app")
import httpx
import asyncio
import time
import json
from services.tag_index import download_and_build_index, is_index_loaded
from services.suggest_pipeline import suggest_with_tags
from services.edhrec import fetch_commander_profile

class FakeDeckCard:
    def __init__(self, name, scryfall_id, board="main"):
        self.card_name = name
        self.scryfall_id = scryfall_id
        self.board = board
        self.quantity = 1

async def main():
    if not is_index_loaded():
        print("Loading tag index...")
        await download_and_build_index()

    # Simulate an Evra deck with a few cards
    print("Fetching EDHREC profile...")
    edhrec = await fetch_commander_profile("Evra, Halcyon Witness")
    print(f"EDHREC: {edhrec['total_decks']} decks, {len(edhrec['cards'])} cards")

    # Fake a small deck
    deck_cards = [
        FakeDeckCard("Evra, Halcyon Witness", "11e2d283-f4eb-4aaa-9014-a0e06c462d4e", "commander"),
    ]
    deck_info = {
        "name": "Halcyon Witness Me",
        "format": "commander",
        "preferences": {"color_identity": ["W"]},
        "strategy_profile": {"primary_strategy": "lifegain voltron"},
    }
    card_lookup = {}

    prompts = [
        "suggest ramp",
        "suggest board wipes",
        "lifegain payoffs",
        "protect my commander",
        "equipment that grants trample",
    ]

    for prompt in prompts:
        print(f"\n{'='*60}")
        print(f"  \"{prompt}\"")
        print(f"{'='*60}")

        result = await suggest_with_tags(
            prompt=prompt,
            deck_cards=deck_cards,
            deck_info=deck_info,
            card_lookup=card_lookup,
            edhrec_profile=edhrec,
        )

        if "error" in result:
            print(f"  ERROR: {result['error']}")
            continue

        print(f"  Summary: {result.get('summary', '')[:100]}")
        print(f"  Suggestions ({len(result.get('suggestions', []))}):")
        for s in result.get("suggestions", []):
            print(f"    {s['card_name']:30s} [{s.get('category', '?')}] - {s.get('reasoning', '')[:60]}")
        debug = result.get("debug", {})
        print(f"  Pool: {debug.get('edhrec_pool', 0)} → filtered: {debug.get('edhrec_filtered', 0)} + scryfall: {debug.get('scryfall_backfill', 0)}")

asyncio.run(main())