import sys
sys.path.insert(0, "/app")
import httpx
import asyncio
import json

async def check():
    async with httpx.AsyncClient() as client:
        r = await client.get("https://api.scryfall.com/cards/named?exact=Sol+Ring", timeout=10)
        data = r.json()
        
        print("=== Card Fields ===")
        print(f"Keywords: {data.get('keywords', [])}")
        print(f"Produced mana: {data.get('produced_mana', [])}")
        print(f"EDHREC rank: {data.get('edhrec_rank')}")
        
        related = data.get("related_uris", {})
        for k, v in related.items():
            print(f"Related: {k} = {v}")

        # Try tagger tags endpoint
        print("\n=== Tagger API ===")
        card_id = data.get("id")
        tagger_url = f"https://api.scryfall.com/cards/{card_id}"
        r2 = await client.get(tagger_url, timeout=10)
        d2 = r2.json()
        for key in ["card_faces", "all_parts", "keywords", "type_line"]:
            if key in d2:
                print(f"{key}: {d2[key]}")

asyncio.run(check())