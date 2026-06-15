import sys
sys.path.insert(0, "/app")
import httpx
import asyncio
import json
import os
import time
from openai import OpenAI
from services.tag_index import get_card_tags, is_index_loaded, get_index_size, download_and_build_index
from data.scryfall_tags import CATEGORY_TAG_GROUPS, ORACLE_FALLBACKS, AVAILABLE_CATEGORIES

def match_category(card_tags, category):
    group = CATEGORY_TAG_GROUPS.get(category, [])
    card_tags_lower = [t.lower() for t in card_tags]
    return any(g.lower() in card_tags_lower for g in group)

def oracle_fallback(oracle_text, category):
    hints = ORACLE_FALLBACKS.get(category, [])
    return any(h.lower() in oracle_text.lower() for h in hints)

def classify_prompt(prompt):
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    system = f"""You classify Magic: The Gathering requests into functional categories.

Available categories:
{json.dumps(AVAILABLE_CATEGORIES)}

Respond with ONLY valid JSON:
{{"categories": ["category1"], "is_specific": false}}

Examples:
"suggest ramp" → {{"categories": ["ramp"], "is_specific": false}}
"protect my commander" → {{"categories": ["protection"], "is_specific": false}}
"board wipes" → {{"categories": ["board_wipe"], "is_specific": false}}
"draw cards" → {{"categories": ["draw"], "is_specific": false}}
"removal spells" → {{"categories": ["removal"], "is_specific": false}}
"counterspells" → {{"categories": ["counterspell"], "is_specific": false}}
"sacrifice outlets" → {{"categories": ["sacrifice"], "is_specific": false}}
"lifegain payoffs" → {{"categories": ["lifegain_payoff"], "is_specific": false}}
"tutor effects" → {{"categories": ["tutor"], "is_specific": false}}
"give my creatures haste" → {{"categories": ["haste_enabler"], "is_specific": false}}"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        temperature=0,
        max_tokens=150,
    )
    content = response.choices[0].message.content.strip()
    content = content.replace("```json", "").replace("```", "").strip()
    return json.loads(content)

async def main():
    if not is_index_loaded():
        print("Loading tag index...")
        ok = await download_and_build_index()
        if not ok:
            print("Failed to download tag index!")
            return
    print(f"Tag index: {get_index_size()} cards")

    # Step 1: Fetch full EDHREC pool
    print("\n=== Loading Full EDHREC Pool ===")
    async with httpx.AsyncClient() as client:
        url = "https://json.edhrec.com/pages/commanders/evra-halcyon-witness.json"
        r = await client.get(url, headers={"User-Agent": "MTGDeckIntelligence/1.0"}, timeout=15)
        data = r.json()

        container = data.get("container", {})
        json_dict = container.get("json_dict", {})
        card_info = json_dict.get("card", {})
        cardlists = json_dict.get("cardlists", [])
        total_decks = card_info.get("num_decks", 0)

        edhrec_cards = []
        seen = set()
        for cardlist in cardlists:
            for card in cardlist.get("cardviews", []):
                name = card.get("name", "")
                if name and name not in seen:
                    seen.add(name)
                    inclusion = card.get("num_decks", 0)
                    pct = round((inclusion / total_decks) * 100, 1) if total_decks else 0
                    edhrec_cards.append({
                        "name": name,
                        "inclusion_pct": pct,
                        "synergy": card.get("synergy", 0),
                    })

        edhrec_cards.sort(key=lambda c: c["inclusion_pct"], reverse=True)
        print(f"EDHREC cards: {len(edhrec_cards)} (from {total_decks} decks)")

        # Step 2: Batch resolve via Scryfall to get oracle_ids
        print("\nResolving via Scryfall (batches of 75)...")
        tagged_pool = []
        for i in range(0, len(edhrec_cards), 75):
            batch = edhrec_cards[i:i+75]
            identifiers = [{"name": c["name"]} for c in batch]
            r2 = await client.post(
                "https://api.scryfall.com/cards/collection",
                json={"identifiers": identifiers},
                timeout=30,
            )
            if r2.status_code == 200:
                resolved = r2.json()
                edhrec_lookup = {c["name"].lower(): c for c in batch}
                for card_data in resolved.get("data", []):
                    name = card_data.get("name", "")
                    oracle_id = card_data.get("oracle_id", "")
                    ecard = edhrec_lookup.get(name.lower(), {})
                    tags = get_card_tags(oracle_id)
                    tagged_pool.append({
                        "name": name,
                        "oracle_id": oracle_id,
                        "tags": tags,
                        "oracle_text": card_data.get("oracle_text", ""),
                        "inclusion_pct": ecard.get("inclusion_pct", 0),
                        "synergy": ecard.get("synergy", 0),
                    })
            await asyncio.sleep(0.15)

        print(f"Tagged pool: {len(tagged_pool)} cards")
        tagged_count = sum(1 for c in tagged_pool if c["tags"])
        print(f"Cards with tags: {tagged_count}/{len(tagged_pool)} ({100*tagged_count//len(tagged_pool)}%)")

    # Step 3: Test prompts against the full pool
    prompts = [
        "suggest ramp",
        "suggest removal",
        "suggest board wipes",
        "ways to draw cards",
        "protect my commander",
        "counterspells",
        "sacrifice outlets",
        "lifegain payoffs",
        "tutor effects",
    ]

    for prompt in prompts:
        print(f"\n{'='*60}")
        print(f"PROMPT: \"{prompt}\"")
        print(f"{'='*60}")

        t = time.time()
        result = classify_prompt(prompt)
        categories = result["categories"]
        print(f"Classify ({time.time() - t:.1f}s): {categories}")

        tag_matches = []
        oracle_matches = []

        for card in tagged_pool:
            source = None
            for cat in categories:
                if match_category(card["tags"], cat):
                    source = "TAG"
                    break
                if oracle_fallback(card["oracle_text"], cat):
                    source = "ORACLE"
                    break

            if source == "TAG":
                tag_matches.append(card)
            elif source == "ORACLE":
                oracle_matches.append(card)

        all_matches = tag_matches + oracle_matches
        # Sort by synergy then inclusion
        all_matches.sort(key=lambda c: (c["synergy"], c["inclusion_pct"]), reverse=True)

        print(f"  Tag: {len(tag_matches)}, Oracle: {len(oracle_matches)}, Total: {len(all_matches)}")
        print(f"  Top 10:")
        for card in all_matches[:10]:
            src = "TAG" if card in tag_matches else "ORC"
            print(f"    [{src}] {card['name']:30s} inc={card['inclusion_pct']:.0f}% syn={card['synergy']:.2f}")

asyncio.run(main())