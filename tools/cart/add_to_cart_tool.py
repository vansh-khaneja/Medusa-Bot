"""
Add to cart tool for LangChain
"""
from langchain.tools import tool
from services.cart import add_to_cart as add_to_cart_service


@tool
def add_to_cart_tool(cart_id: str, variant_id: str, quantity: int, auth_token: str, x_publishable_api_key: str) -> str:
    """
    Add a product variant to the shopping cart.
    Use when user wants to add items to cart, buy a product, or add variants to their cart.

    Args:
        cart_id: The cart ID
        variant_id: The product variant ID to add
        quantity: Quantity to add (default: 1)
        auth_token: Customer authentication token
        x_publishable_api_key: Store publishable API key

    Returns:
        Formatted string confirming the addition
    """
    result = add_to_cart_service(cart_id, variant_id, quantity, auth_token, x_publishable_api_key)

    if "error" in result:
        return f"❌ {result['error']}"

    # Format the response
    # Find the item that was just added (last item or matching variant_id)
    added_item = None
    for item in result.get('items', []):
        if item['variant_id'] == variant_id:
            added_item = item
            break

    response = "✅ Added to cart!\n\n"

    if added_item:
        response += f"📦 {added_item['product_title']}"
        if added_item.get('variant_title'):
            response += f" - {added_item['variant_title']}"
        response += f"\n   Quantity: {added_item['quantity']}\n"
        response += f"   Price: {added_item['unit_price']}\n\n"

    response += f"🛒 Cart Summary:\n"
    response += f"Items: {result['items_count']}\n"
    response += f"Total: {result['totals']['total']}"

    return response
