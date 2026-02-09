"""
Tool for searching products in the store
"""
from langchain.tools import tool
from services.search import search_products


@tool
def search_products_tool(query: str, limit: int = 5) -> str:
    """
    Search for products in the store using Meilisearch. Use this when the user asks for product
    suggestions, wants to find items, or searches for specific products like "tshirt", "shoes",
    "dress", etc.

    Args:
        query: The search query (e.g., "tshirt", "shoes", "jeans")
        limit: Maximum number of products to show (default: 5)

    Returns:
        A formatted string with product search results
    """
    try:
        result = search_products(query, limit=limit)

        products = result.get("products", [])
        total_hits = result.get("total_hits", 0)

        if not products:
            return f"No products found for '{query}'. Try a different search term."

        response = f"🔍 Found {total_hits} product(s) for '{query}':\n\n"

        for i, product in enumerate(products, 1):
            response += f"{i}. **{product.get('title', 'Untitled Product')}**\n"

            # Add description if available
            description = product.get('description')
            if description:
                # Truncate long descriptions
                desc_preview = description[:100] + "..." if len(description) > 100 else description
                response += f"   {desc_preview}\n"

            # Show minimum price if available
            min_price = product.get('minimum_price')
            if min_price:
                response += f"   Starting at: ${min_price:.2f}\n"

            # Add categories if available
            categories = product.get('categories', [])
            if categories:
                category_names = [cat.get('name', '') for cat in categories if isinstance(cat, dict)]
                if category_names:
                    response += f"   Category: {', '.join(category_names)}\n"

            response += "\n"

        return response.strip()

    except Exception as e:
        return f"Error searching for products: {str(e)}"
