"""
Tool for searching products by price
"""
from langchain.tools import tool
from services.search import search_products_by_price


@tool
def search_products_by_price_tool(query: str, max_price: float, limit: int = 5) -> str:
    """
    Search for products under a specific price. Use when user asks for products with price
    constraints like "under $50", "less than $20", "cheap products", etc.

    Args:
        query: The search query (e.g., "tshirt", "shoes", "jeans")
        max_price: Maximum price in dollars (e.g., 50 for "under $50")
        limit: Maximum number of products to show (default: 5)

    Returns:
        A formatted string with product search results filtered by price
    """
    try:
        result = search_products_by_price(query, max_price, limit=limit)

        products = result.get("products", [])
        total_hits = result.get("total_hits", 0)

        if not products:
            return f"No products found for '{query}' under ${max_price}. Try a different search or higher price."

        response = f"🔍 Found {total_hits} product(s) for '{query}' under ${max_price}:\n\n"

        for i, product in enumerate(products, 1):
            response += f"{i}. **{product.get('title', 'Untitled Product')}**\n"

            # Add description if available
            description = product.get('description')
            if description:
                # Truncate long descriptions
                desc_preview = description[:100] + "..." if len(description) > 100 else description
                response += f"   {desc_preview}\n"

            # Show minimum price
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
