"""
Product variants tool for LangChain
"""
from langchain.tools import tool
from services.products import get_product_by_id as get_product_service


@tool
def get_product_tool(product_id: str, x_publishable_api_key: str) -> str:
    """
    Get detailed information about a product including all available variants, sizes, colors, and options.
    Use when user asks about product variants, available options, sizes, colors, or specific product details by ID.

    Args:
        product_id: The product ID to retrieve
        x_publishable_api_key: Store publishable API key

    Returns:
        Formatted string with product and variants details
    """
    product = get_product_service(product_id, x_publishable_api_key)

    if "error" in product:
        return f"❌ {product['error']}"

    # Format the response
    result = f"🛍️ {product['title']}\n\n"

    # Description
    if product.get('description'):
        result += f"{product['description']}\n\n"

    # Available options
    if product.get('options'):
        result += "📋 Available Options:\n"
        for option in product['options']:
            values = ", ".join(option['values'])
            result += f"• {option['title']}: {values}\n"
        result += "\n"

    # Variants
    if product.get('variants'):
        result += f"🎨 Variants ({len(product['variants'])}):\n\n"
        for i, variant in enumerate(product['variants'], 1):
            result += f"{i}. {variant['title']}\n"
            result += f"   SKU: {variant['sku']}\n"

            # Show options for this variant
            if variant.get('options'):
                options_str = ", ".join([f"{k}: {v}" for k, v in variant['options'].items()])
                result += f"   Options: {options_str}\n"

            result += "\n"

    return result.strip()
