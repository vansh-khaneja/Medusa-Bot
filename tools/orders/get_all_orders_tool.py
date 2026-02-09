"""
Tool for retrieving all customer orders
"""
from langchain.tools import tool
from services.orders import list_orders


@tool
def get_customer_orders_tool(auth_token: str, x_publishable_api_key: str, limit: int = 10) -> str:
    """
    Get all orders for the authenticated customer. Use this when the user asks about their orders,
    order history, past purchases, or wants to see what they've ordered.

    Args:
        auth_token: Customer authentication token
        x_publishable_api_key: Store publishable API key
        limit: Maximum number of orders to retrieve (default: 10)

    Returns:
        A formatted string with all orders information
    """
    try:
        orders = list_orders(auth_token, x_publishable_api_key, limit=limit)

        if not orders:
            return "You don't have any orders yet."

        result = f"You have {len(orders)} order(s):\n\n"
        for order in orders:
            result += f"📦 Order #{order['display_id']}\n"
            result += f"   Status: {order['status']}\n"
            result += f"   Payment: {order['payment_status']}\n"
            result += f"   Fulfillment: {order['fulfillment_status']}\n"
            result += f"   Total: {order['overall_price']} {order['currency_code']}\n"
            result += f"   Items: {len(order['products'])} product(s)\n\n"

        return result
    except Exception as e:
        return f"Error fetching orders: {str(e)}"
