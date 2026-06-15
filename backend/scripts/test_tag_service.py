import sys
sys.path.insert(0, "/app")
import asyncio
from services.tag_index import get_card_tags, download_and_build_index, is_index_loaded, get_index_size

async def test():
    # Try loading from disk first
    if not is_index_loaded():
        print("No index on disk, downloading...")
        ok = await download_and_build_index()
        if not ok:
            print("Download failed!")
            return

    print(f"Index loaded: {get_index_size()} cards")

    # Test known oracle_ids (Sol Ring, Path to Exile)
    # We need to look these up
    import httpx
    async with httpx.AsyncClient() as client:
        test_cards = [
            "Sol Ring", "Path to Exile", "Lightning Greaves",
            "Wrath of God", "Skullclamp", "Aetherflux Reservoir",
        ]
        for name in test_cards:
            r = await client.get(f"https://api.scryfall.com/cards/named?exact={name}", timeout=10)
            if r.status_code == 200:
                card = r.json()
                oracle_id = card.get("oracle_id", "")
                tags = get_card_tags(oracle_id)
                print(f"  {name}: {tags[:6]}")
            await asyncio.sleep(0.12)

asyncio.run(test())