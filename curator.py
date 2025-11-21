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

        // Log the page title to verify we got the right page
        log.info(`Page title: ${$('title').text()}`);
        log.info(`Current URL: ${request.url}`);

        // Try to find the main search results container first
        const resultContainers = [
            '.search-results',
            '#search-results',
            '.results',
            '#results',
            '.product-list',
            '.products',
            'main',
            '#main',
            '.content',
            '#content'
        ];

        let $container = null;
        for (const containerSelector of resultContainers) {
            const $found = $(containerSelector);
            if ($found.length > 0) {
                log.info(`Found container: ${containerSelector}`);
                $container = $found;
                break;
            }
        }

        // If no container found, use the whole page but skip header/footer/nav
        if (!$container) {
            log.info('No specific container found, using body');
            $container = $('body');
        }

        // Get all images from container but filter based on parent elements
        log.info('Finding all images and filtering by parent context');

        const $allImages = $container.find('img');
        log.info(`Total images in container: ${$allImages.length}`);

        // Filter out images that are in excluded sections
        const $images = $allImages.filter((i, img) => {
            const $img = $(img);
            const $parents = $img.parents();

            // Exclude images in these containers
            if ($parents.filter('.sidebar, #sidebar, .featured, .popular, .recommended, .trending, aside, .widget, header, footer, nav, .navigation, .menu').length > 0) {
                return false;
            }

            // Exclude images in header/footer/nav directly
            if ($img.closest('header, footer, nav, aside, .sidebar').length > 0) {
                return false;
            }

            return true;
        });

        log.info(`Images after filtering out sidebars/headers/footers: ${$images.length}`)

        // Track seen URLs to avoid duplicates
        const seenUrls = new Set();

        // Process each image
        $images.each((index, img) => {
            const $img = $(img);

            // Handle lazy loading: check multiple attributes
            let imageUrl = $img.attr('data-src') ||
                          $img.attr('data-lazy-src') ||
                          $img.attr('data-original') ||
                          $img.attr('src');

            // Skip if no image URL
            if (!imageUrl) return;

            // Get alt text for filtering
            const altText = ($img.attr('alt') || '').toLowerCase();

            // Skip placeholder/loading images
            if (imageUrl.includes('placeholder') ||
                imageUrl.includes('loading') ||
                imageUrl.includes('blank.') ||
                imageUrl.includes('logo') ||
                imageUrl.includes('icon')) return;

            // Skip non-artwork images based on alt text
            const skipAltTexts = [
                'logo',
                'meisterdrucke',
                'deutsch',
                'english',
                'français',
                'español',
                'italiano',
                'dhl',
                'post.at',
                'quehenberger',
                'cargoboard',
                'fedex',
                'ups',
                'shipping',
                'payment',
                'visa',
                'mastercard',
                'paypal',
                'erfahrungen',
                'bewertungen',
                'reviews',
                'rating'
            ];

            if (skipAltTexts.some(skip => altText.includes(skip))) {
                return;
            }

            // Also skip if alt text is very short (likely not artwork)
            if (altText.length > 0 && altText.length < 5) {
                return;
            }

            // Skip very small images (likely icons/UI elements)
            const width = parseInt($img.attr('width')) || parseInt($img.css('width')) || 0;
            const height = parseInt($img.attr('height')) || parseInt($img.css('height')) || 0;

            // Filter out images that are definitely too small (less than 100px in either dimension)
            if ((width > 0 && width < 100) || (height > 0 && height < 100)) {
                return;
            }

            // Make URL absolute if relative
            if (imageUrl.startsWith('//')) {
                imageUrl = 'https:' + imageUrl;
            } else if (imageUrl.startsWith('/')) {
                imageUrl = 'https://www.meisterdrucke.ie' + imageUrl;
            } else if (!imageUrl.startsWith('http')) {
                imageUrl = 'https://www.meisterdrucke.ie/' + imageUrl;
            }

            // Skip duplicates
            if (seenUrls.has(imageUrl)) {
                return;
            }
            seenUrls.add(imageUrl);

            // Get title from alt text or parent link
            const $link = $img.closest('a');
            let title = $img.attr('alt') || $img.attr('title') || $link.attr('title') || '';

            // Clean up title
            title = title.trim();
            if (!title || title.length < 2) {
                title = 'Untitled';
            }

            // Try to extract artist name
            let artist = 'Unknown Artist';

            // Look for artist in parent elements
            const $parent = $img.closest('div, li, article');
            const $artistEl = $parent.find('.artist, .artist-name, [class*="artist"]').first();
            if ($artistEl.length > 0 && $artistEl.text().trim()) {
                artist = $artistEl.text().trim();
            } else {
                // Try to extract from title
                const titleLower = title.toLowerCase();
                if (titleLower.includes(' by ')) {
                    const parts = title.split(/ by /i);
                    if (parts.length > 1) {
                        artist = parts[1].split(',')[0].split('(')[0].trim();
                    }
                } else if (titleLower.includes(' - ')) {
                    const parts = title.split(' - ');
                    if (parts.length >= 2) {
                        // Usually format is "Title - Artist" or "Title - Artist, Year"
                        artist = parts[1].split(',')[0].split('(')[0].trim();
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

        // Push all results to dataset at once (much faster than one-by-one)
        if (results.length > 0) {
            await context.pushData(results);
        }
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
            # pageFunction pushes an array, so we need to flatten it
            if isinstance(item, list):
                results.extend(item)
            elif isinstance(item, dict):
                results.append(item)

        # Limit results
        results = results[:max_results]

        return results

    except Exception as e:
        raise CuratorError(f"Scraping failed: {str(e)}")
