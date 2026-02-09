"""
Tool for retrieving detailed information about a specific order
"""
from langchain.tools import tool
from services.orders import get_order


@tool
def get_order_details_tool(auth_token: str, x_publishable_api_key: str, display_id: int) -> str:
    """
    Get detailed information about a specific order by its display ID. Use this when the user
    asks about a specific order number, wants to track an order, or needs details about a particular purchase.

    Args:
        auth_token: Customer authentication token
        x_publishable_api_key: Store publishable API key
        display_id: The order display ID (the order number shown to customers)

    Returns:
        A formatted string with detailed order information
    """
    try:
        order = get_order(auth_token, x_publishable_api_key, display_id)

        if "error" in order:
            return f"Order #{display_id} not found. Please check the order number and try again."

        result = f"📦 Order #{order['display_id']} Details:\n\n"
        result += f"Order ID: {order['order_id']}\n"
        result += f"Status: {order['status']}\n"
        result += f"Payment Status: {order['payment_status']}\n"
        result += f"Fulfillment Status: {order['fulfillment_status']}\n"
        result += f"Total: {order['overall_price']} {order['currency_code']}\n"
        result += f"Placed At: {order.get('placed_at', 'N/A')}\n\n"

        result += "🛍️ Products:\n"
        for i, product in enumerate(order['products'], 1):
            result += f"{i}. {product['title']}\n"
            if product.get('variant'):
                result += f"   Variant: {product['variant']}\n"
            result += f"   Quantity: {product['quantity']}\n"
            result += f"   Price: {product['unit_price']} each\n"
            result += f"   Line Total: {product['line_total']}\n\n"

        if order.get('shipping_address'):
            addr = order['shipping_address']
            result += f"📍 Shipping Address:\n"
            result += f"   {addr.get('address_1', '')}\n"
            if addr.get('address_2'):
                result += f"   {addr['address_2']}\n"
            result += f"   {addr.get('city', '')}, {addr.get('province', '')} {addr.get('postal_code', '')}\n"
            result += f"   {addr.get('country_code', '')}\n"

        return result
    except Exception as e:
        return f"Error fetching order details: {str(e)}"
