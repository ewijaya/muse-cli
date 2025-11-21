"""
curator.py - Scraper Layer for Muse CLI
Handles Apify interaction to scrape artwork from Meisterdrucke gallery.
"""

import os
from typing import List, Dict
from urllib.parse import quote_plus
from apify_client import ApifyClient


class CuratorError(Exception):
    """Custom exception for curator errors."""
    pass


def search_art(keywords: str, max_results: int = 10) -> List[Dict[str, str]]:
    """
    Search for artwork on Meisterdrucke using the provided keywords.

    Args:
        keywords: Space-separated search keywords
        max_results: Maximum number of results to return (default: 10)

    Returns:
        List of dictionaries containing artwork information:
        - title: Artwork title
        - artist: Artist name
        - image_url: URL to the artwork image

    Raises:
        CuratorError: If API token is missing or scraping fails
    """
    api_token = os.getenv("APIFY_TOKEN")
    if not api_token:
        raise CuratorError("APIFY_TOKEN environment variable not set")

    # Initialize Apify client
    client = ApifyClient(api_token)

    # URL encode keywords (replace spaces with +)
    encoded_keywords = quote_plus(keywords)
    target_url = f"https://www.meisterdrucke.ie/suche/{encoded_keywords}.html"

    # Page function for cheerio-scraper
    # This JavaScript will be executed by the scraper
    page_function = """
    async function pageFunction(context) {
        const { $, request, log } = context;

        const results = [];

        // Select all search result items
        $('.search-result-item, .search-result a img').each((index, element) => {
            const $el = $(element);

            // Get the image element
            const $img = $el.is('img') ? $el : $el.find('img').first();

            if ($img.length === 0) return;

            // Handle lazy loading: check data-src first, then src
            let imageUrl = $img.attr('data-src') || $img.attr('src');

            // Skip if no image URL
            if (!imageUrl) return;

            // Make URL absolute if relative
            if (imageUrl.startsWith('//')) {
                imageUrl = 'https:' + imageUrl;
            } else if (imageUrl.startsWith('/')) {
                imageUrl = 'https://www.meisterdrucke.ie' + imageUrl;
            }

            // Filter out small images (icons, thumbnails < 200px)
            const width = parseInt($img.attr('width')) || 0;
            if (width > 0 && width < 200) return;

            // Get title and artist information
            const $link = $el.is('a') ? $el : $el.closest('a');
            const title = $img.attr('alt') || $link.attr('title') || 'Untitled';

            // Try to extract artist name from various possible locations
            let artist = 'Unknown Artist';
            const $artistEl = $el.find('.artist, .artist-name').first();
            if ($artistEl.length > 0) {
                artist = $artistEl.text().trim();
            } else {
                // Try to extract from title or alt text
                const titleText = title.toLowerCase();
                if (titleText.includes(' by ')) {
                    artist = title.split(' by ')[1].split(',')[0].trim();
                } else if (titleText.includes(' - ')) {
                    const parts = title.split(' - ');
                    if (parts.length > 1) {
                        artist = parts[parts.length - 1].trim();
                    }
                }
            }

            results.push({
                title: title,
                artist: artist,
                image_url: imageUrl
            });
        });

        log.info(`Found ${results.length} artwork results`);

        return results;
    }
    """

    # Configure the scraper run
    run_input = {
        "startUrls": [{"url": target_url}],
        "pageFunction": page_function,
        "proxyConfiguration": {"useApifyProxy": True},
        "maxRequestsPerCrawl": 1,  # Only scrape the search results page
    }

    try:
        # Run the actor
        run = client.actor("apify/cheerio-scraper").call(run_input=run_input)

        # Fetch results from dataset
        results = []
        for item in client.dataset(run["defaultDatasetId"]).iterate_items():
            # The pageFunction returns an array, so we need to flatten it
            if isinstance(item, list):
                results.extend(item)
            elif isinstance(item, dict):
                results.append(item)

        # Limit results
        results = results[:max_results]

        return results

    except Exception as e:
        raise CuratorError(f"Scraping failed: {str(e)}")
