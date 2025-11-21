"""
gallery_apis.py - API-based Art Gallery Sources for Muse CLI
Handles integration with official museum and gallery APIs.
"""

import os
import requests
from typing import List, Dict
from urllib.parse import quote_plus


class GalleryAPIError(Exception):
    """Custom exception for gallery API errors."""
    pass


def search_met_museum(keywords: str, max_results: int = 10) -> List[Dict[str, str]]:
    """
    Search the Metropolitan Museum of Art API.

    Args:
        keywords: Space-separated search keywords
        max_results: Maximum number of results to return (default: 10)

    Returns:
        List of dictionaries containing artwork information:
        - title: Artwork title
        - artist: Artist name
        - image_url: URL to the artwork image

    Raises:
        GalleryAPIError: If the API request fails
    """
    try:
        # Step 1: Search for object IDs
        search_url = f"https://collectionapi.metmuseum.org/public/collection/v1/search"
        params = {
            "q": keywords,
            "hasImages": "true"  # Only return objects with images
        }

        response = requests.get(search_url, params=params, timeout=30)
        response.raise_for_status()
        search_data = response.json()

        object_ids = search_data.get("objectIDs", [])
        if not object_ids:
            return []

        # Limit to max_results
        object_ids = object_ids[:max_results * 2]  # Fetch more since some may not have images

        # Step 2: Fetch details for each object
        results = []
        for object_id in object_ids:
            if len(results) >= max_results:
                break

            try:
                object_url = f"https://collectionapi.metmuseum.org/public/collection/v1/objects/{object_id}"
                obj_response = requests.get(object_url, timeout=10)
                obj_response.raise_for_status()
                obj_data = obj_response.json()

                # Extract artwork details
                title = obj_data.get("title", "Untitled")
                artist = obj_data.get("artistDisplayName", "Unknown Artist")

                # Get primary image (prefer primary, fallback to additional)
                image_url = obj_data.get("primaryImage") or obj_data.get("primaryImageSmall")

                if not image_url:
                    continue  # Skip if no image

                # Clean up artist name
                if not artist or artist.strip() == "":
                    artist = "Unknown Artist"

                results.append({
                    "title": title,
                    "artist": artist,
                    "image_url": image_url
                })

            except (requests.RequestException, ValueError, KeyError):
                # Skip this object if there's an error
                continue

        return results

    except requests.RequestException as e:
        raise GalleryAPIError(f"Met Museum API request failed: {str(e)}")
    except Exception as e:
        raise GalleryAPIError(f"Met Museum API error: {str(e)}")


def search_wikiart(keywords: str, max_results: int = 10) -> List[Dict[str, str]]:
    """
    Search WikiArt API for paintings.

    Args:
        keywords: Space-separated search keywords
        max_results: Maximum number of results to return (default: 10)

    Returns:
        List of dictionaries containing artwork information:
        - title: Artwork title
        - artist: Artist name
        - image_url: URL to the artwork image

    Raises:
        GalleryAPIError: If the API request fails
    """
    try:
        # WikiArt search endpoint
        search_url = "https://www.wikiart.org/en/Search/Painting"
        params = {
            "term": keywords,
            "page": 1
        }

        response = requests.get(search_url, params=params, timeout=30)
        response.raise_for_status()

        # WikiArt returns HTML, but we can use their internal API
        # Try the JSON endpoint instead
        api_url = f"https://www.wikiart.org/en/api/2/PaintingSearch"
        api_params = {
            "term": keywords,
            "imageFormat": "Large"
        }

        api_response = requests.get(api_url, params=api_params, timeout=30)
        api_response.raise_for_status()
        data = api_response.json()

        paintings = data.get("data", [])
        if not paintings:
            return []

        # Limit results
        paintings = paintings[:max_results]

        results = []
        for painting in paintings:
            title = painting.get("title", "Untitled")
            artist = painting.get("artistName", "Unknown Artist")

            # Get image URL
            image_url = painting.get("image")

            if not image_url:
                continue

            # Make URL absolute if needed
            if not image_url.startswith("http"):
                image_url = f"https://uploads.wikiart.org/images/{painting.get('contentId', '')}/{image_url}"

            results.append({
                "title": title,
                "artist": artist,
                "image_url": image_url
            })

        return results

    except requests.RequestException as e:
        raise GalleryAPIError(f"WikiArt API request failed: {str(e)}")
    except Exception as e:
        raise GalleryAPIError(f"WikiArt API error: {str(e)}")


def search_art_api(source: str, keywords: str, max_results: int = 10) -> List[Dict[str, str]]:
    """
    Unified function to search any supported art gallery API.

    Args:
        source: Gallery source ("met", "wikiart")
        keywords: Space-separated search keywords
        max_results: Maximum number of results to return

    Returns:
        List of artwork dictionaries

    Raises:
        GalleryAPIError: If the source is invalid or the API request fails
    """
    sources = {
        "met": search_met_museum,
        "wikiart": search_wikiart
    }

    if source not in sources:
        raise GalleryAPIError(f"Invalid source: {source}. Choose from: {', '.join(sources.keys())}")

    return sources[source](keywords, max_results)
