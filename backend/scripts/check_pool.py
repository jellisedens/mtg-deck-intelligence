import sys
sys.path.insert(0, "/app")
import httpx
import asyncio

async def check():
    async with httpx.AsyncClient() as client:
        # Fetch Evra EDHREC profile directly
        url = "https://json.edhrec.com/pages/commanders/evra-halcyon-witness.json"
        r = await client.get(url, headers={"User-Agent": "MTGDeckIntelligence/1.0"}, timeout=15)
        data = r.json()
        
        container = data.get("container", {})
        json_dict = container.get("json_dict", {})
        card_info = json_dict.get("card", {})
        cardlists = json_dict.get("cardlists", [])
        total_decks = card_info.get("num_decks", 0)
        
        all_cards = []
        seen = set()
        for cardlist in cardlists:
            for card in cardlist.get("cardviews", []):
                name = card.get("name", "")
                if name and name not in seen:
                    seen.add(name)
                    inclusion = card.get("num_decks", 0)
                    pct = round((inclusion / total_decks) * 100, 1) if total_decks else 0
                    all_cards.append({"name": name, "pct": pct, "synergy": card.get("synergy", 0)})
        
        all_cards.sort(key=lambda c: c["pct"], reverse=True)
        
        print(f"Commander: Evra, Halcyon Witness")
        print(f"Total decks analyzed: {total_decks}")
        print(f"Total unique cards: {len(all_cards)}")
        
        over50 = [c for c in all_cards if c["pct"] >= 50]
        over30 = [c for c in all_cards if c["pct"] >= 30]
        over20 = [c for c in all_cards if c["pct"] >= 20]
        over10 = [c for c in all_cards if c["pct"] >= 10]
        
        print(f"\nOver 50%: {len(over50)} cards")
        print(f"Over 30%: {len(over30)} cards")
        print(f"Over 20%: {len(over20)} cards")
        print(f"Over 10%: {len(over10)} cards")
        print(f"All: {len(all_cards)} cards")
        
        print(f"\nCurrently loading: 75 (capped)")
        print(f"Cards we're MISSING at 75 cap with >=20%: {max(0, len(over20) - 75)}")

asyncio.run(check())