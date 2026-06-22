# Save to backend/scripts/test_card_tagger.py
import sys
sys.path.insert(0, "/app")
import httpx
import asyncio
from services.tag_index import download_and_build_index, is_index_loaded
from services.card_tagger import get_card_roles, get_deck_role_distribution, get_deck_gaps, format_deck_intelligence

class FakeCard:
    def __init__(self, name, sid, qty=1):
        self.card_name = name
        self.scryfall_id = sid
        self.quantity = qty
        self.board = "main"

async def main():
    if not is_index_loaded():
        await download_and_build_index()

    # Fetch some known cards
    async with httpx.AsyncClient() as client:
        test_cards = [
            "Sol Ring", "Arcane Signet", "Mind Stone",
            "Path to Exile", "Swords to Plowshares", "Generous Gift",
            "Wrath of God", "Fumigate",
            "Skullclamp", "War Room", "Sensei's Divining Top",
            "Lightning Greaves", "Swiftfoot Boots",
            "Aetherflux Reservoir", "Serra Ascendant",
            "Plains", "Plains", "Plains",
        ]

        card_lookup = {}
        deck_cards = []
        for name in test_cards:
            r = await client.get(f"https://api.scryfall.com/cards/named?exact={name}", timeout=10)
            if r.status_code == 200:
                card = r.json()
                card_lookup[card["id"]] = card
                deck_cards.append(FakeCard(name, card["id"]))
            await asyncio.sleep(0.12)

        # Test individual card roles
        print("=== Individual Card Roles ===")
        for card in deck_cards:
            data = card_lookup.get(card.scryfall_id, {})
            roles = get_card_roles(data.get("oracle_id", ""), data.get("oracle_text", ""), data.get("type_line", ""))
            print(f"  {card.card_name}: {roles}")

        # Test deck distribution
        print("\n=== Deck Role Distribution ===")
        dist = get_deck_role_distribution(deck_cards, card_lookup)
        for role, count in sorted(dist["counts"].items(), key=lambda x: x[1], reverse=True):
            print(f"  {role}: {count}")
        if dist["untagged"]:
            print(f"\n  Untagged: {dist['untagged']}")

        # Test gap detection
        print("\n=== Deck Gaps ===")
        gaps = get_deck_gaps(dist)
        for gap in gaps:
            print(f"  {gap['role']}: have {gap['have']}/{gap['target']} ({gap['priority']})")

        # Test formatted output
        print("\n=== Formatted Intelligence ===")
        print(format_deck_intelligence(dist, gaps))

asyncio.run(main())