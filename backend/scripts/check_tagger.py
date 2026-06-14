import sys
sys.path.insert(0, "/app")
import httpx
import asyncio

async def check():
    async with httpx.AsyncClient() as client:
        tags = [
            # Already confirmed
            "ramp", "removal", "board-wipe", "boardwipe", "counter",
            "draw", "card-advantage", "cantrip", "lifegain", "protection",
            "evasion", "tutor", "sacrifice-outlet", "recursion", "reanimate",
            "graveyard-hate", "mana-dork", "mana-rock", "land-ramp",
            # New from catalog
            "anthem", "combat-trick", "pump", "blink", "flicker",
            "bounce", "fog", "goad", "damage-doubler", "damage-multiplier",
            "damage-tripler", "extra-turn", "extra-combat-phase", "extra-land",
            "death-trigger", "attack-trigger", "enchantress", "cost-reducer",
            "drain-life", "burn", "alternate-win-condition", "mill", "discard",
            "group-hug", "group-slug", "freeze", "hatebear", "grows",
            "free-sac-outlet", "counterspell", "disenchant",
            "creature-removal", "artifact-removal", "enchantment-removal",
            "spot-removal", "mass-removal",
            "graveyard-fuel", "exile", "donate",
            "copy", "clone", "steal", "gating",
            "extra-untap", "animate", "flicker-creature",
            "wheel", "loot", "impulse-draw",
        ]

        working = []
        for tag in tags:
            r = await client.get(
                f"https://api.scryfall.com/cards/search?q=otag:{tag}+f:commander",
                timeout=10,
            )
            if r.status_code == 200:
                total = r.json().get("total_cards", 0)
                working.append({"tag": tag, "count": total})
            await asyncio.sleep(0.1)

        print(f"=== {len(working)} WORKING TAGS ===")
        for t in sorted(working, key=lambda x: x["count"], reverse=True):
            print(f"  otag:{t['tag']}: {t['count']}")

asyncio.run(check())