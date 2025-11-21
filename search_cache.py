"""
search_cache.py - Cache Layer for Muse CLI
Stores the last search results to enable the 'explain' command.
"""

import json
import os
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path


class CacheError(Exception):
    """Custom exception for cache errors."""
    pass


def get_cache_dir() -> Path:
    """Get or create the cache directory."""
    cache_dir = Path.home() / ".muse-cli"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def get_cache_file() -> Path:
    """Get the path to the cache file."""
    return get_cache_dir() / "last_search.json"


def save_search_results(original_query: str, keywords: str, artworks: List[Dict[str, str]], source: str) -> None:
    """
    Save search results to cache.

    Args:
        original_query: The original philosophical text/quote from the user
        keywords: The generated search keywords
        artworks: List of artwork dictionaries (title, artist, image_url)
        source: The gallery source used (meisterdrucke, met, wikiart)

    Raises:
        CacheError: If saving fails
    """
    try:
        cache_data = {
            "timestamp": datetime.now().isoformat(),
            "original_query": original_query,
            "keywords": keywords,
            "source": source,
            "artworks": artworks
        }

        cache_file = get_cache_file()
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, indent=2, ensure_ascii=False)

    except Exception as e:
        raise CacheError(f"Failed to save search results: {str(e)}")


def load_search_results() -> Optional[Dict]:
    """
    Load the last search results from cache.

    Returns:
        Dictionary containing:
        - timestamp: ISO format timestamp
        - original_query: The original user query
        - keywords: Generated keywords
        - source: Gallery source
        - artworks: List of artwork dictionaries

        Returns None if no cache exists or cache is invalid.

    Raises:
        CacheError: If loading fails
    """
    cache_file = get_cache_file()

    if not cache_file.exists():
        return None

    try:
        with open(cache_file, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)

        # Validate required fields
        required_fields = ["timestamp", "original_query", "keywords", "artworks"]
        if not all(field in cache_data for field in required_fields):
            return None

        return cache_data

    except (json.JSONDecodeError, IOError) as e:
        raise CacheError(f"Failed to load search results: {str(e)}")


def get_artwork_by_index(index: int) -> Optional[Dict[str, str]]:
    """
    Get a specific artwork from the cached search results.

    Args:
        index: 1-based index of the artwork (as shown to the user)

    Returns:
        Artwork dictionary or None if not found

    Raises:
        CacheError: If loading fails or no cache exists
    """
    cache_data = load_search_results()

    if cache_data is None:
        raise CacheError("No previous search found. Run 'muse search' first.")

    artworks = cache_data.get("artworks", [])

    # Convert to 0-based index
    array_index = index - 1

    if array_index < 0 or array_index >= len(artworks):
        raise CacheError(f"Invalid index {index}. Last search had {len(artworks)} results.")

    return {
        "artwork": artworks[array_index],
        "original_query": cache_data["original_query"],
        "keywords": cache_data["keywords"],
        "source": cache_data.get("source", "unknown")
    }


def clear_cache() -> bool:
    """
    Clear the search cache.

    Returns:
        True if cache was cleared, False if no cache existed
    """
    cache_file = get_cache_file()

    if cache_file.exists():
        cache_file.unlink()
        return True

    return False
