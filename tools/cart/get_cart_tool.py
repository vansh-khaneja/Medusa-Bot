"""
Cart tool for LangChain
"""
from langchain.tools import tool
from services.cart import get_cart as get_cart_service


@tool
def get_cart_tool(cart_id: str, auth_token: str, x_publishable_api_key: str) -> str:
    """
    Get the shopping cart details including all items.
    Use when user asks about their cart, shopping cart, or items in cart.

    Args:
        cart_id: The cart ID to retrieve
        auth_token: Customer authentication token
        x_publishable_api_key: Store publishable API key

    Returns:
        Formatted string with cart details
    """
    cart = get_cart_service(cart_id, auth_token, x_publishable_api_key)

    if "error" in cart:
        return f"❌ {cart['error']}"

    # Format the response
    result = f"🛒 Your Shopping Cart\n\n"
    result += f"Cart ID: {cart['cart_id']}\n"
    result += f"Email: {cart['email']}\n"
    result += f"Currency: {cart['currency_code'].upper()}\n\n"

    if not cart['items']:
        return result + "Your cart is empty."

    result += f"Items ({len(cart['items'])}):\n"
    for i, item in enumerate(cart['items'], 1):
        result += f"\n{i}. {item['product_title']}"
        if item.get('variant_title'):
            result += f" ({item['variant_title']})"
        result += f"\n   SKU: {item.get('variant_sku', 'N/A')}\n"
        result += f"   Quantity: {item['quantity']}\n"
        result += f"   Price: {item['unit_price']} {cart['currency_code']} each\n"
        result += f"   Subtotal: {item['subtotal']} {cart['currency_code']}\n"

    result += f"\n📊 Cart Totals:\n"
    result += f"Subtotal: {cart['totals']['subtotal']} {cart['currency_code']}\n"

    if cart['totals']['discount_total'] > 0:
        result += f"Discount: -{cart['totals']['discount_total']} {cart['currency_code']}\n"

    if cart['totals']['tax_total'] > 0:
        result += f"Tax: {cart['totals']['tax_total']} {cart['currency_code']}\n"

    if cart['totals']['shipping_total'] > 0:
        result += f"Shipping: {cart['totals']['shipping_total']} {cart['currency_code']}\n"

    result += f"Total: {cart['totals']['total']} {cart['currency_code']}\n"

    return result
