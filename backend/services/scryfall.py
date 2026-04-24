import httpx
import asyncio
import json
from datetime import datetime, timedelta
from typing import Optional



class ScryfallCache:
    """
    Simple in-memory cache with expiration.
    Stores Scryfall responses for 1 hour to reduce API calls.
    """

    def __init__(self, ttl_minutes: int = 60):
        self._cache: dict = {}
        self._ttl = timedelta(minutes=ttl_minutes)

    def get(self, key: str) -> Optional[dict]:
        if key in self._cache:
            entry = self._cache[key]
            if datetime.utcnow() - entry["timestamp"] < self._ttl:
                return entry["data"]
            else:
                del self._cache[key]
        return None

    def set(self, key: str, data: dict):
        self._cache[key] = {
            "data": data,
            "timestamp": datetime.utcnow(),
        }


class ScryfallService:
    """
    Service layer for interacting with the Scryfall API.
    Handles rate limiting, caching, and error handling.
    """

    BASE_URL = "https://api.scryfall.com"
    REQUEST_DELAY = 0.1  # 100ms between requests (Scryfall guideline)
    HEADERS = {
        "User-Agent": "MTGDeckIntelligence/1.0",
        "Accept": "application/json",
    }

    def __init__(self):
        self._cache = ScryfallCache()
        self._last_request_time: Optional[datetime] = None

    async def _rate_limit(self):
        """Enforce 100ms delay between requests to respect Scryfall's guidelines."""
        if self._last_request_time:
            elapsed = (datetime.utcnow() - self._last_request_time).total_seconds()
            if elapsed < self.REQUEST_DELAY:
                await asyncio.sleep(self.REQUEST_DELAY - elapsed)
        self._last_request_time = datetime.utcnow()

    async def _get(self, endpoint: str, params: dict = None) -> dict:
        """Make a GET request to Scryfall with rate limiting and error handling."""
        await self._rate_limit()

        url = f"{self.BASE_URL}{endpoint}"
        cache_key = f"{endpoint}:{params}"

        # Check cache first
        cached = self._cache.get(cache_key)
        if cached:
            return cached

        async with httpx.AsyncClient(headers=self.HEADERS) as client:
            response = await client.get(url, params=params, timeout=10.0)

            if response.status_code == 200:
                data = response.json()
                self._cache.set(cache_key, data)
                return data
            elif response.status_code == 404:
                return {"error": "not_found", "details": "No cards found matching your search."}
            else:
                return {"error": "api_error", "details": f"Scryfall returned status {response.status_code}"}

    async def _post(self, endpoint: str, json_data: dict) -> dict:
        """Make a POST request to Scryfall with rate limiting, caching, and error handling."""
        # Cache key for POST requests
        cache_key = f"POST:{endpoint}:{json.dumps(json_data, sort_keys=True)}"
        cached = self._cache.get(cache_key)
        if cached:
            return cached

        await self._rate_limit()
        url = f"{self.BASE_URL}{endpoint}"
        async with httpx.AsyncClient(headers=self.HEADERS) as client:
            response = await client.post(url, json=json_data, timeout=30.0)
            if response.status_code == 200:
                data = response.json()
                self._cache.set(cache_key, data)
                return data
            else:
                return {"error": "api_error", "details": f"Scryfall returned status {response.status_code}"}

    async def search_cards(self, query: str, page: int = 1) -> dict:
        """
        Search for cards using Scryfall syntax.
        Automatically filters for Commander-legal cards.
        """
        full_query = f"{query} f:commander"

        return await self._get("/cards/search", {
            "q": full_query,
            "page": page,
            "format": "json",
        })

    async def search_cards_raw(self, query: str, page: int = 1) -> dict:
        """
        Search for cards using raw Scryfall syntax.
        Does NOT add any format filters — the AI controls the full query.
        """
        return await self._get("/cards/search", {
            "q": query,
            "page": page,
            "format": "json",
        })

    async def get_card_by_name(self, name: str, fuzzy: bool = False) -> dict:
        """
        Get a single card by name.
        Use fuzzy=True for approximate matching (handles misspellings).
        """
        param_key = "fuzzy" if fuzzy else "exact"
        return await self._get("/cards/named", {param_key: name})

    async def get_card_by_id(self, scryfall_id: str) -> dict:
        """Get a single card by its Scryfall UUID."""
        return await self._get(f"/cards/{scryfall_id}")

    async def get_collection(self, identifiers: list[dict]) -> dict:
        """
        Fetch up to 75 cards at once by their identifiers.
        Each identifier should be a dict like {"id": "scryfall-uuid"}
        or {"name": "Sol Ring"}.
        Useful for loading all cards in a deck in one call.
        """
        results = []
        not_found = []

        for i in range(0, len(identifiers), 75):
            batch = identifiers[i:i + 75]
            data = await self._post("/cards/collection", {"identifiers": batch})

            if "error" in data:
                return data

            results.extend(data.get("data", []))
            not_found.extend(data.get("not_found", []))

        return {"data": results, "not_found": not_found}

    async def autocomplete(self, query: str) -> dict:
        """
        Get up to 20 card name suggestions for autocomplete.
        Fast endpoint — not cached since Scryfall handles it efficiently.
        """
        await self._rate_limit()

        async with httpx.AsyncClient(headers=self.HEADERS) as client:
            response = await client.get(
                f"{self.BASE_URL}/cards/autocomplete",
                params={"q": query},
                timeout=5.0,
            )

            if response.status_code == 200:
                return response.json()
            else:
                return {"error": "api_error", "details": f"Autocomplete failed with status {response.status_code}"}


# Singleton instance — shared across the app
scryfall_service = ScryfallService()