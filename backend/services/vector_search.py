"""
Vector search service for MTG cards.
Combines pre-filtering (color, CMC, type, format) with semantic similarity search.

Usage:
    from services.vector_search import vector_search
    results = await vector_search(
        query="cheap sacrifice outlets",
        color_identity=["B", "G"],
        format_legal="commander",
        max_cmc=3,
        limit=10,
    )
"""

import os
import re
from typing import Optional

from openai import OpenAI
from sqlalchemy import text
from sqlalchemy.orm import Session

from database.session import SessionLocal

client = OpenAI()
EMBEDDING_MODEL = "text-embedding-3-small"


def _embed_query(query: str) -> list[float]:
    """Generate embedding for a search query."""
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=query,
    )
    return response.data[0].embedding


def _extract_filters_from_query(query: str) -> dict:
    """
    Extract hard filters from natural language query.
    Returns extracted filters and the remaining semantic query.

    Examples:
        "cheap green creatures" -> {max_cmc: 3, colors: ["G"], types: ["creature"], query: "creatures"}
        "instant speed removal under 2 mana" -> {max_cmc: 2, types: ["instant"], query: "removal"}
        "black card draw" -> {colors: ["B"], query: "card draw"}
    """
    filters = {}
    remaining = query.lower().strip()

    # Extract color references
    color_map = {
        "white": "W", "blue": "U", "black": "B", "red": "R", "green": "G",
        "azorius": "WU", "dimir": "UB", "rakdos": "BR", "gruul": "RG", "selesnya": "GW",
        "orzhov": "WB", "izzet": "UR", "golgari": "BG", "boros": "RW", "simic": "GU",
        "esper": "WUB", "grixis": "UBR", "jund": "BRG", "naya": "RGW", "bant": "GWU",
        "abzan": "WBG", "jeskai": "URW", "sultai": "BGU", "mardu": "RWB", "temur": "GUR",
        "colorless": "",
    }

    found_colors = set()
    for color_word, color_letters in color_map.items():
        if color_word in remaining:
            for letter in color_letters:
                found_colors.add(letter)
            remaining = remaining.replace(color_word, "").strip()

    # Also check single letter color codes
    single_color_pattern = r'\b([wubrg])\b'
    for match in re.finditer(single_color_pattern, remaining):
        found_colors.add(match.group(1).upper())
        remaining = remaining[:match.start()] + remaining[match.end():]

    if found_colors:
        filters["colors"] = list(found_colors)

    # Extract CMC/cost references
    cmc_patterns = [
        (r'(?:under|below|less than|cmc\s*<?=?\s*)(\d+)\s*(?:mana|cmc)?', "max_cmc"),
        (r'(?:over|above|more than|cmc\s*>?=?\s*)(\d+)\s*(?:mana|cmc)?', "min_cmc"),
        (r'(?:exactly|cmc\s*=?\s*)(\d+)\s*(?:mana|cmc)', "exact_cmc"),
    ]

    for pattern, key in cmc_patterns:
        match = re.search(pattern, remaining)
        if match:
            filters[key] = int(match.group(1))
            remaining = remaining[:match.start()] + remaining[match.end():]

    # Extract cost descriptors
    cost_words = {
        "cheap": ("max_cmc", 3),
        "very cheap": ("max_cmc", 2),
        "low cost": ("max_cmc", 3),
        "low cmc": ("max_cmc", 3),
        "expensive": ("min_cmc", 5),
        "high cost": ("min_cmc", 5),
        "high cmc": ("min_cmc", 5),
    }

    for phrase, (key, value) in cost_words.items():
        if phrase in remaining:
            if key not in filters:
                filters[key] = value
            remaining = remaining.replace(phrase, "").strip()

    # Extract type references
    type_map = {
        "creature": "Creature",
        "creatures": "Creature",
        "instant": "Instant",
        "instants": "Instant",
        "sorcery": "Sorcery",
        "sorceries": "Sorcery",
        "enchantment": "Enchantment",
        "enchantments": "Enchantment",
        "artifact": "Artifact",
        "artifacts": "Artifact",
        "planeswalker": "Planeswalker",
        "planeswalkers": "Planeswalker",
        "land": "Land",
        "lands": "Land",
        "equipment": "Equipment",
        "aura": "Aura",
        "auras": "Aura",
    }

    found_types = []
    for type_word, type_name in type_map.items():
        # Match whole word only
        if re.search(r'\b' + type_word + r'\b', remaining):
            if type_name not in found_types:
                found_types.append(type_name)
            remaining = re.sub(r'\b' + type_word + r'\b', '', remaining).strip()

    if found_types:
        filters["types"] = found_types

    # Extract "instant speed" as a type filter
    if "instant speed" in remaining or "instant-speed" in remaining:
        if "types" not in filters:
            filters["types"] = []
        if "Instant" not in filters.get("types", []):
            filters.setdefault("types", []).append("Instant")
        remaining = remaining.replace("instant speed", "").replace("instant-speed", "").strip()

    # Clean up remaining query
    remaining = re.sub(r'\s+', ' ', remaining).strip()
    # Remove dangling articles and prepositions
    remaining = re.sub(r'^(a |an |the |some |any |i need |i want |find |show |get )', '', remaining)
    remaining = remaining.strip()

    filters["semantic_query"] = remaining if remaining else query

    return filters


def vector_search(
    query: str,
    color_identity: Optional[list[str]] = None,
    format_legal: Optional[str] = "commander",
    max_cmc: Optional[float] = None,
    min_cmc: Optional[float] = None,
    card_types: Optional[list[str]] = None,
    exclude_cards: Optional[list[str]] = None,
    roles: Optional[list[str]] = None,
    limit: int = 10,
    auto_filter: bool = True,
    db: Optional[Session] = None,
) -> list[dict]:
    """
    Search for cards using semantic similarity with optional pre-filtering.

    Args:
        query: Natural language search query
        color_identity: Filter to cards within this color identity (e.g., ["B", "G"])
        format_legal: Filter to cards legal in this format (default: commander)
        max_cmc: Maximum converted mana cost
        min_cmc: Minimum converted mana cost
        card_types: Filter to specific card types (e.g., ["Creature", "Instant"])
        exclude_cards: List of card names to exclude (already in deck)
        roles: Filter to cards with specific roles (e.g., ["ramp", "removal_single"])
        limit: Number of results to return
        auto_filter: Automatically extract filters from query text
        db: Optional database session (creates one if not provided)

    Returns:
        List of card dicts with similarity scores
    """
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        # Auto-extract filters from query
        extracted = {}
        semantic_query = query
        if auto_filter:
            extracted = _extract_filters_from_query(query)
            semantic_query = extracted.pop("semantic_query", query)

            # Merge extracted filters with explicit ones (explicit take priority)
            if not color_identity and "colors" in extracted:
                color_identity = extracted["colors"]
            if max_cmc is None and "max_cmc" in extracted:
                max_cmc = extracted["max_cmc"]
            if min_cmc is None and "min_cmc" in extracted:
                min_cmc = extracted["min_cmc"]
            if not card_types and "types" in extracted:
                card_types = extracted["types"]

        # Generate query embedding
        query_embedding = _embed_query(semantic_query)
        emb_str = '[' + ','.join(str(x) for x in query_embedding) + ']'

        # Build SQL with filters
        where_clauses = ["embedding IS NOT NULL"]
        params = {"emb": emb_str, "limit": limit}

        # Color identity filter — card's color identity must be subset of allowed colors
        if color_identity:
            color_list = list(set(color_identity))
            color_placeholders = ", ".join(f"'{c}'" for c in color_list)
            where_clauses.append(f"""
                NOT EXISTS (
                    SELECT 1 FROM jsonb_array_elements_text(color_identity::jsonb) c
                    WHERE c::text NOT IN ({color_placeholders})
                )
            """)

        # Format legality filter
        if format_legal:
            where_clauses.append(f"legalities->>'{ format_legal}' = 'legal'")

        # CMC filters
        if max_cmc is not None:
            where_clauses.append(f"cmc <= {max_cmc}")
        if min_cmc is not None:
            where_clauses.append(f"cmc >= {min_cmc}")

        # Type filter
        if card_types:
            type_conditions = []
            for t in card_types:
                type_conditions.append(f"type_line ILIKE '%{t}%'")
            where_clauses.append(f"({' OR '.join(type_conditions)})")

        # Role filter
        if roles:
            role_conditions = []
            for r in roles:
                role_conditions.append(f"roles::text ILIKE '%\"{r}\"%'")
            where_clauses.append(f"({' OR '.join(role_conditions)})")

        # Exclude cards already in deck
        if exclude_cards:
            excluded = ", ".join(f"'{name.replace(chr(39), chr(39)+chr(39))}'" for name in exclude_cards)
            where_clauses.append(f"LOWER(name) NOT IN ({excluded.lower()})")

        where_sql = " AND ".join(where_clauses)

        sql = f"""
            SELECT
                scryfall_id, name, type_line, oracle_text, mana_cost, cmc,
                colors, color_identity, rarity, power, toughness,
                prices, image_uris, roles, archetypes, search_terms,
                synergies, power_level, strategic_summary, edhrec_rank,
                1 - (embedding <=> CAST(:emb AS vector)) as similarity,
                (1 - (embedding <=> CAST(:emb AS vector))) *
                    CASE
                        WHEN edhrec_rank IS NULL THEN 0.7
                        WHEN edhrec_rank <= 50 THEN 1.15
                        WHEN edhrec_rank <= 200 THEN 1.1
                        WHEN edhrec_rank <= 500 THEN 1.05
                        WHEN edhrec_rank <= 1000 THEN 1.0
                        WHEN edhrec_rank <= 5000 THEN 0.95
                        ELSE 0.85
                    END as combined_score
            FROM cards
            WHERE {where_sql}
            ORDER BY combined_score DESC
            LIMIT :limit
        """

        result = db.execute(text(sql), params)

        cards = []
        for row in result:
            cards.append({
                "scryfall_id": row.scryfall_id,
                "name": row.name,
                "type_line": row.type_line,
                "oracle_text": (row.oracle_text or "")[:200],
                "mana_cost": row.mana_cost,
                "cmc": row.cmc,
                "colors": row.colors,
                "color_identity": row.color_identity,
                "rarity": row.rarity,
                "power": row.power,
                "toughness": row.toughness,
                "prices": row.prices,
                "image_uris": row.image_uris,
                "roles": row.roles,
                "archetypes": row.archetypes,
                "search_terms": row.search_terms,
                "synergies": row.synergies,
                "power_level": row.power_level,
                "strategic_summary": row.strategic_summary,
                "similarity": round(float(row.similarity), 4),
                "edhrec_rank": row.edhrec_rank,
                "combined_score": round(float(row.combined_score), 4),
            })

        return cards

    finally:
        if close_db:
            db.close()


def search_with_context(
    query: str,
    deck_color_identity: Optional[list[str]] = None,
    deck_card_names: Optional[list[str]] = None,
    deck_format: str = "commander",
    limit: int = 15,
    db: Optional[Session] = None,
) -> dict:
    """
    High-level search that extracts filters, runs vector search,
    and returns results with context about what was filtered.

    This is the main function AI suggest should call.
    """
    # Extract filters from query
    extracted = _extract_filters_from_query(query)
    semantic_query = extracted.pop("semantic_query", query)

    # Use deck color identity if not specified in query
    colors = extracted.get("colors") or deck_color_identity

    results = vector_search(
        query=semantic_query,
        color_identity=colors,
        format_legal=deck_format,
        max_cmc=extracted.get("max_cmc"),
        min_cmc=extracted.get("min_cmc"),
        card_types=extracted.get("types"),
        exclude_cards=deck_card_names,
        limit=limit,
        auto_filter=False,  # We already extracted filters
        db=db,
    )

    return {
        "query": query,
        "semantic_query": semantic_query,
        "filters_applied": {
            "colors": colors,
            "format": deck_format,
            "max_cmc": extracted.get("max_cmc"),
            "min_cmc": extracted.get("min_cmc"),
            "types": extracted.get("types"),
            "excluded_cards": len(deck_card_names) if deck_card_names else 0,
        },
        "results": results,
        "result_count": len(results),
    }