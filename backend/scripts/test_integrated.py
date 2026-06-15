import sys
sys.path.insert(0, "/app")
import httpx
import asyncio
import time
from services.tag_index import get_card_tags, download_and_build_index, is_index_loaded, get_index_size
from services.tag_classifier import classify_tags, filter_by_category

async def load_edhrec_pool():
    """Load full EDHREC pool, resolve via Scryfall, tag every card."""
    async with httpx.AsyncClient() as client:
        url = "https://json.edhrec.com/pages/commanders/evra-halcyon-witness.json"
        r = await client.get(url, headers={"User-Agent": "MTGDeckIntelligence/1.0"}, timeout=15)
        data = r.json()

        container = data.get("container", {})
        json_dict = container.get("json_dict", {})
        card_info = json_dict.get("card", {})
        cardlists = json_dict.get("cardlists", [])
        total_decks = card_info.get("num_decks", 0)

        edhrec_cards = []
        seen = set()
        for cardlist in cardlists:
            for card in cardlist.get("cardviews", []):
                name = card.get("name", "")
                if name and name not in seen:
                    seen.add(name)
                    inclusion = card.get("num_decks", 0)
                    pct = round((inclusion / total_decks) * 100, 1) if total_decks else 0
                    edhrec_cards.append({
                        "name": name,
                        "inclusion_pct": pct,
                        "synergy": card.get("synergy", 0),
                    })

        # Batch resolve
        tagged_pool = []
        for i in range(0, len(edhrec_cards), 75):
            batch = edhrec_cards[i:i+75]
            identifiers = [{"name": c["name"]} for c in batch]
            r2 = await client.post(
                "https://api.scryfall.com/cards/collection",
                json={"identifiers": identifiers},
                timeout=30,
            )
            if r2.status_code == 200:
                lookup = {c["name"].lower(): c for c in batch}
                for card_data in r2.json().get("data", []):
                    name = card_data.get("name", "")
                    ecard = lookup.get(name.lower(), {})
                    tagged_pool.append({
                        "name": name,
                        "oracle_text": card_data.get("oracle_text", ""),
                        "tags": get_card_tags(card_data.get("oracle_id", "")),
                        "inclusion_pct": ecard.get("inclusion_pct", 0),
                        "synergy": ecard.get("synergy", 0),
                        "cmc": card_data.get("cmc", 0),
                        "type_line": card_data.get("type_line", ""),
                        "mana_cost": card_data.get("mana_cost", ""),
                    })
            await asyncio.sleep(0.15)

        return tagged_pool

async def main():
    # Load tag index
    if not is_index_loaded():
        print("Downloading tag index...")
        await download_and_build_index()
    print(f"Tag index: {get_index_size()} cards")

    # Load pool
    t = time.time()
    pool = await load_edhrec_pool()
    print(f"Pool loaded: {len(pool)} cards in {time.time() - t:.1f}s")

    # Test prompts
    prompts = [
        "suggest ramp",
        "suggest removal",
        "board wipes",
        "ways to draw cards",
        "protect my commander",
        "counterspells",
        "lifegain payoffs",
        "sacrifice outlets",
        "tutor effects",
        "give my creatures haste",
        "suggest cards for this deck",
        "any more ramp I can add",
        "equipment that grants trample",
    ]

    for prompt in prompts:
        print(f"\n{'='*60}")
        print(f"  \"{prompt}\"")
        print(f"{'='*60}")

        t = time.time()
        classification = classify_tags(prompt)
        cats = classification["categories"]
        specific = classification["is_specific"]
        print(f"  Categories: {cats} (specific={specific}) [{time.time()-t:.1f}s]")

        if "general" in cats:
            print(f"  General request — show top cards by synergy")
            top = sorted(pool, key=lambda c: c["synergy"], reverse=True)[:8]
            for c in top:
                print(f"    {c['name']:30s} syn={c['synergy']:.2f} inc={c['inclusion_pct']:.0f}%")
            continue

        filtered = filter_by_category(pool, cats)
        filtered.sort(key=lambda c: (c["synergy"], c["inclusion_pct"]), reverse=True)

        tag_count = sum(1 for c in filtered if c.get("_match_source") == "tag")
        oracle_count = sum(1 for c in filtered if c.get("_match_source") == "oracle")
        print(f"  Matches: {len(filtered)} (tag={tag_count}, oracle={oracle_count})")
        print(f"  Top 8:")
        for c in filtered[:8]:
            src = "TAG" if c.get("_match_source") == "tag" else "ORC"
            print(f"    [{src}] {c['name']:30s} syn={c['synergy']:.2f} inc={c['inclusion_pct']:.0f}%")

asyncio.run(main())