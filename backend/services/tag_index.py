"""
Scryfall Oracle Tag Index Service.

Downloads the bulk Oracle Tags file and builds an inverted index:
  oracle_id → [functional_tags]

Used to instantly classify any card's functional role.
Refreshed weekly, cached in memory and on disk.
"""

import os
import json
import time
import httpx
import asyncio
import logging

logger = logging.getLogger(__name__)

CACHE_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "oracle_tags_index.json")
BULK_API_URL = "https://api.scryfall.com/bulk-data/oracle_tags"

# In-memory index: oracle_id → [tag_labels]
_index = None
_last_loaded = 0


def get_card_tags(oracle_id: str) -> list:
    """Get functional tags for a card by oracle_id. Returns empty list if not tagged."""
    global _index
    if _index is None:
        _load_from_disk()
    if _index is None:
        return []
    return _index.get(oracle_id, [])


def get_cards_by_tags(oracle_ids: list, tag_groups: list) -> list:
    """Filter a list of oracle_ids to those matching any tag in tag_groups."""
    global _index
    if _index is None:
        _load_from_disk()
    if _index is None:
        return oracle_ids

    tag_set = set(t.lower() for t in tag_groups)
    matches = []
    for oid in oracle_ids:
        card_tags = _index.get(oid, [])
        if any(t.lower() in tag_set for t in card_tags):
            matches.append(oid)
    return matches


def is_index_loaded() -> bool:
    return _index is not None and len(_index) > 0


def get_index_size() -> int:
    if _index is None:
        return 0
    return len(_index)


def _load_from_disk():
    """Load cached index from disk into memory."""
    global _index, _last_loaded
    resolved = os.path.abspath(CACHE_PATH)
    if os.path.exists(resolved):
        try:
            with open(resolved) as f:
                _index = json.load(f)
            _last_loaded = time.time()
            logger.info(f"Tag index loaded from disk: {len(_index)} cards")
        except Exception as e:
            logger.warning(f"Failed to load tag index from disk: {e}")
            _index = {}
    else:
        logger.warning(f"No tag index on disk at {resolved}")
        _index = {}


async def download_and_build_index():
    """Download Oracle Tags bulk file and build the inverted index."""
    global _index, _last_loaded

    async with httpx.AsyncClient() as client:
        # Get download URL
        r = await client.get(BULK_API_URL, timeout=10)
        if r.status_code != 200:
            logger.error(f"Failed to get bulk data URL: {r.status_code}")
            return False

        url = r.json().get("download_uri", "")
        if not url:
            logger.error("No download_uri in bulk data response")
            return False

        # Download
        t = time.time()
        r2 = await client.get(url, timeout=120)
        if r2.status_code != 200:
            logger.error(f"Failed to download oracle tags: {r2.status_code}")
            return False

        raw_tags = r2.json()
        logger.info(f"Downloaded {len(raw_tags)} tag entries in {time.time() - t:.1f}s")

        # Build inverted index
        index = {}
        for entry in raw_tags:
            if entry.get("type") != "oracle":
                continue
            label = entry.get("label", "")
            if not label:
                continue
            for tagging in entry.get("taggings", []):
                oid = tagging.get("oracle_id", "")
                if oid:
                    if oid not in index:
                        index[oid] = []
                    index[oid].append(label)

        _index = index
        _last_loaded = time.time()
        logger.info(f"Built tag index: {len(index)} cards")

        # Save to disk
        try:
            resolved = os.path.abspath(CACHE_PATH)
            os.makedirs(os.path.dirname(resolved), exist_ok=True)
            with open(resolved, "w") as f:
                json.dump(index, f)
            logger.info(f"Saved tag index to {resolved}")
        except Exception as e:
            logger.warning(f"Failed to save tag index: {e}")

        return True