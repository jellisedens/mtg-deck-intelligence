import httpx
import asyncio
import json

async def test():
    async with httpx.AsyncClient() as client:
        resp = await client.get("https://archidekt.com/api/decks/1/", timeout=10.0)
        data = resp.json()
        cards = data.get("cards", [])
        if cards:
            card_data = cards[0].get("card", {})
            print(f"Card keys: {list(card_data.keys())}")
            # Look for name and oracle id / scryfall connection
            print(f"Card name: {card_data.get('name', 'N/A')}")
            print(f"Oracle ID: {card_data.get('oracleId', 'N/A')}")
            print(f"UID: {card_data.get('uid', 'N/A')}")
            # Check for scryfall-related fields
            for key in card_data:
                val = card_data[key]
                if isinstance(val, str) and "scryfall" in str(val).lower():
                    print(f"Scryfall field - {key}: {val}")
                if isinstance(val, str) and len(val) == 36 and "-" in val:
                    print(f"UUID field - {key}: {val}")

        # Also check deck-level info
        print(f"\nDeck format: {data.get('deckFormat', 'N/A')}")
        print(f"Deck name: {data.get('name', 'N/A')}")
        print(f"Description: {str(data.get('description', ''))[:100]}")

asyncio.run(test())