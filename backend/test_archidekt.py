import httpx
import asyncio
import json

async def test():
    async with httpx.AsyncClient() as client:
        resp = await client.get("https://archidekt.com/api/decks/1/", timeout=10.0)
        data = resp.json()
        cards = data.get("cards", [])
        
        for i, entry in enumerate(cards[:3]):
            card = entry.get("card", {})
            oracle = card.get("oracleCard", {})
            print(f"\n--- Card {i+1} ---")
            print(f"displayName: {card.get('displayName', 'N/A')}")
            print(f"uid: {card.get('uid', 'N/A')}")
            print(f"edition: {json.dumps(card.get('edition', {}))[:200]}")
            print(f"categories: {entry.get('categories', [])}")
            print(f"quantity: {entry.get('quantity', 0)}")
            print(f"oracleCard keys: {list(oracle.keys()) if oracle else 'N/A'}")
            if oracle:
                print(f"  oracle name: {oracle.get('name', 'N/A')}")
                print(f"  oracle scryfallId: {oracle.get('scryfallId', 'N/A')}")
                print(f"  oracle oracleId: {oracle.get('oracleId', 'N/A')}")
        
        # Check deck format mapping
        print(f"\nDeck format code: {data.get('deckFormat', 'N/A')}")

asyncio.run(test())