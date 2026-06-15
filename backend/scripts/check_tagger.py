import sys
sys.path.insert(0, "/app")
import httpx
import asyncio

async def check():
    async with httpx.AsyncClient() as client:
        # Compare: how many cards SHOULD be ramp vs how many are TAGGED as ramp
        queries = [
            # Tagged ramp vs oracle-text ramp
            ("otag:ramp f:commander id<=W", "Tagged ramp"),
            ('o:"{T}: Add" f:commander id<=W', "Oracle ramp (tap add)"),
            ('o:"search your library" o:land f:commander id<=W', "Oracle ramp (land search)"),
            
            # Tagged removal vs oracle-text removal  
            ("otag:removal f:commander id<=W", "Tagged removal"),
            ('o:"destroy target" f:commander id<=W', "Oracle removal (destroy)"),
            ('o:"exile target" f:commander id<=W', "Oracle removal (exile)"),
            
            # Tagged draw vs oracle-text draw
            ("otag:draw f:commander id<=W", "Tagged draw"),
            ('o:"draw a card" f:commander id<=W', "Oracle draw"),
        ]
        
        print("=== Tag Coverage vs Oracle Text ===")
        for query, label in queries:
            r = await client.get(
                f"https://api.scryfall.com/cards/search?q={query}",
                timeout=10,
            )
            if r.status_code == 200:
                total = r.json().get("total_cards", 0)
                print(f"  {label}: {total}")
            else:
                print(f"  {label}: 0 (not found)")
            await asyncio.sleep(0.1)

        # Check some recent/new cards for tag coverage
        print("\n=== Recent Card Tag Coverage ===")
        recent_cards = [
            "Fomalhaut, Forbidden Star",
            "White Lotus Tile", 
            "Loran of the Third Path",
            "Caretaker's Talent",
            "Get Lost",
            "Sunfall",
            "Moonshaker Cavalry",
            "Esper Sentinel",
            "Smothering Tithe",
        ]
        
        core_tags = ["ramp", "removal", "draw", "protection", "lifegain", "board-wipe"]
        
        for card in recent_cards:
            card_tags = []
            for tag in core_tags:
                r = await client.get(
                    f'https://api.scryfall.com/cards/search?q=!"{card}"+otag:{tag}',
                    timeout=10,
                )
                if r.status_code == 200:
                    card_tags.append(tag)
                await asyncio.sleep(0.1)
            
            if card_tags:
                print(f"  {card}: {card_tags}")
            else:
                print(f"  {card}: NO TAGS")

asyncio.run(check())