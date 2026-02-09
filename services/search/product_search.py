"""
Service for searching products in Meilisearch
"""
import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def search_products(query: str, limit: int = 10):
    """
    Search for products using Meilisearch.

    Args:
        query: The search query (e.g., "tshirt", "shoes", "dress")
        limit: Maximum number of results to return (default: 10)

    Returns:
        List of product dictionaries with search results
    """
    # Get Meilisearch configuration from environment
    meilisearch_host = os.getenv("MEILISEARCH_HOST")
    meilisearch_api_key = os.getenv("MEILISEARCH_API_KEY")
    index_name = os.getenv("MEILISEARCH_INDEX")

    if not all([meilisearch_host, meilisearch_api_key, index_name]):
        raise ValueError("Missing Meilisearch configuration in environment variables")

    # Construct the search URL
    url = f"{meilisearch_host}/indexes/{index_name}/search"

    # Set up headers
    headers = {
        "Authorization": f"Bearer {meilisearch_api_key}",
        "Content-Type": "application/json"
    }

    # Prepare search payload
    payload = {
        "q": query,
        "limit": limit,
        "showRankingScore": True  # Include ranking score
    }

    # Make the search request
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()

    # Parse the response
    search_results = response.json()

    # Extract and clean the product data
    products = []
    for hit in search_results.get("hits", []):
        # Filter by ranking score > 0.5
        ranking_score = hit.get("_rankingScore", 0)
        if ranking_score <= 0.5:
            continue

        product_data = {
            "id": hit.get("id"),
            "title": hit.get("title"),
            "description": hit.get("description"),
            "handle": hit.get("handle"),
            "thumbnail": hit.get("thumbnail"),
            "minimum_price": hit.get("minimum_price"),
            "categories": hit.get("categories", []),
            "tags": hit.get("tags", []),
            "ranking_score": ranking_score,  # Include ranking score
            # Include any other fields that might be present
            "variants": hit.get("variants", []),
            "options": hit.get("options", []),
            "images": hit.get("images", [])
        }
        products.append(product_data)

    return {
        "query": query,
        "total_hits": search_results.get("estimatedTotalHits", 0),
        "products": products,
        "processing_time_ms": search_results.get("processingTimeMs", 0)
    }
