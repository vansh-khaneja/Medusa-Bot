"""
Service for retrieving a single order
"""
import requests
from .list import list_orders


def get_order(auth_token: str, x_publishable_api_key: str, display_id: int):
    """
    Retrieve detailed information about a specific order.

    Args:
        auth_token: Customer authentication token
        x_publishable_api_key: Store publishable API key
        display_id: The order display ID (customer-facing order number)

    Returns:
        Dictionary with detailed order information
    """
    orders = list_orders(auth_token, x_publishable_api_key)
    order_id = None
    for order in orders:
        if order["display_id"] == display_id:
            order_id = order["order_id"]
            break
    if not order_id:
        return {"error": "Order with provided display_id not found."}
    url = f"http://localhost:9000/store/orders/{order_id}"
    headers = {
        "Authorization": f"Bearer {auth_token}",
        "x-publishable-api-key": x_publishable_api_key,
        "Content-Type": "application/json"
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    order_response = response.json().get("order", {})
    formatted_order = {
        "order_id": order_response.get("id"),
        "display_id": order_response.get("display_id"),
        "status": order_response.get("status"),
        "payment_status": order_response.get("payment_status"),
        "fulfillment_status": order_response.get("fulfillment_status"),
        "currency_code": order_response.get("currency_code"),
        "overall_price": order_response.get("total"),
        "products": [],
        "shipping_address": order_response.get("shipping_address"),
        "billing_address": order_response.get("billing_address"),
        "placed_at": order_response.get("created_at")
    }
    for item in order_response.get("items", []):
        product_data = {
            "product_id": item.get("product_id"),
            "variant_id": item.get("variant_id"),
            "title": item.get("product_title") or item.get("title"),
            "description": item.get("product_description"),
            "variant": item.get("variant_title"),
            "thumbnail": item.get("thumbnail"),
            "unit_price": item.get("unit_price"),
            "quantity": item.get("quantity"),
            "line_total": item.get("total")
        }
        formatted_order["products"].append(product_data)
    return formatted_order
