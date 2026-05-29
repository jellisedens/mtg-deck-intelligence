"""
EDHREC Integration Test Script
Usage: docker exec mtg-backend python /app/scripts/test_edhrec.py "Belbe, Corrupted Observer"
"""

import sys
import asyncio
import json

sys.path.insert(0, "/app")

from services.edhrec import fetch_commander_profile


async def test(commander_name: str):
    print(f"Fetching EDHREC data for: {commander_name}")
    print("=" * 60)

    profile = await fetch_commander_profile(commander_name)

    if not profile:
        print("ERROR: No profile returned. Check commander name spelling.")
        return

    print(f"Commander:      {profile.get('commander_name')}")
    print(f"Total decks:    {profile.get('total_decks')}")
    print(f"Cards tracked:  {len(profile.get('cards', []))}")
    print(f"Themes:         {profile.get('themes', [])[:5]}")
    print(f"Combos:         {len(profile.get('combos', []))}")

    cards = profile.get("cards", [])
    if not cards:
        print("\nNo cards found in profile.")
        return

    # Top 20 by synergy score
    print("\n--- Top 20 by Synergy ---")
    sorted_syn = sorted(cards, key=lambda c: c.get("synergy", 0), reverse=True)
    for i, c in enumerate(sorted_syn[:20], 1):
        print(
            "  %2d. %5.1f%%  syn:%+.2f  [%-20s]  %s"
            % (
                i,
                c.get("inclusion_pct", 0),
                c.get("synergy", 0),
                c.get("category", "?"),
                c.get("name", "?"),
            )
        )

    # Top 20 by inclusion percentage
    print("\n--- Top 20 by Inclusion % ---")
    sorted_inc = sorted(cards, key=lambda c: c.get("inclusion_pct", 0), reverse=True)
    for i, c in enumerate(sorted_inc[:20], 1):
        print(
            "  %2d. %5.1f%%  syn:%+.2f  [%-20s]  %s"
            % (
                i,
                c.get("inclusion_pct", 0),
                c.get("synergy", 0),
                c.get("category", "?"),
                c.get("name", "?"),
            )
        )

    # Category breakdown
    print("\n--- Cards by Category ---")
    categories = {}
    for c in cards:
        cat = c.get("category", "unknown")
        categories[cat] = categories.get(cat, 0) + 1
    for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
        print(f"  {cat}: {count}")

    # Full JSON dump option
    if "--json" in sys.argv:
        print("\n--- Full Profile JSON ---")
        print(json.dumps(profile, indent=2, default=str))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_edhrec.py \"Commander Name\"")
        print("       python test_edhrec.py \"Commander Name\" --json")
        sys.exit(1)

    commander = sys.argv[1]
    asyncio.run(test(commander))