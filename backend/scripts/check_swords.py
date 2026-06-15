import sys
sys.path.insert(0, "/app")
import httpx
import asyncio

async def check():
    async with httpx.AsyncClient() as client:
        # Exact name search
        r = await client.get("https://api.scryfall.com/cards/named?exact=Swords+to+Plowshares", timeout=10)
        card = r.json()
        print(f"Name: {card.get('name')}")
        print(f"Layout: {card.get('layout')}")
        print(f"Set: {card.get('set_name')}")
        print(f"ID: {card.get('id')}")
        if card.get("card_faces"):
            for face in card["card_faces"]:
                print(f"  Face: {face.get('name')}")

        # Also try fuzzy
        print("\n--- Fuzzy search ---")
        r2 = await client.get("https://api.scryfall.com/cards/named?fuzzy=Swords+to+Plowshares", timeout=10)
        card2 = r2.json()
        print(f"Name: {card2.get('name')}")
        print(f"Layout: {card2.get('layout')}")
        print(f"Set: {card2.get('set_name')}")

        # Search for all versions
        print("\n--- All versions ---")
        r3 = await client.get('https://api.scryfall.com/cards/search?q=!"Swords to Plowshares"&unique=prints&order=released&dir=desc', timeout=10)
        if r3.status_code == 200:
            data = r3.json()
            for c in data.get("data", [])[:5]:
                layout = c.get("layout", "")
                name = c.get("name", "")
                set_name = c.get("set_name", "")
                print(f"  {name} | {layout} | {set_name}")

asyncio.run(check())