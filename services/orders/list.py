"""
Service for listing all orders
"""
import requests


def list_orders(auth_token: str, x_publishable_api_key: str, limit: int = 10, offset: int = 0):
    """
    Retrieve all orders for the authenticated customer.

    Args:
        auth_token: Customer authentication token
        x_publishable_api_key: Store publishable API key
        limit: Maximum number of orders to retrieve
        offset: Number of orders to skip

    Returns:
        List of order dictionaries with cleaned/formatted data
    """
    url = "http://localhost:9000/store/orders"
    headers = {
        "Authorization": f"Bearer {auth_token}",
        "x-publishable-api-key": x_publishable_api_key,
        "Content-Type": "application/json"
    }
    params = {
        "limit": limit,
        "offset": offset
    }
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    orders_response = response.json()
    clean_orders = []
    for order in orders_response.get("orders", []):
        order_data = {
            "order_id": order.get("id"),
            "display_id": order.get("display_id"),
            "status": order.get("status"),
            "payment_status": order.get("payment_status"),
            "fulfillment_status": order.get("fulfillment_status"),
            "currency_code": order.get("currency_code"),
            "overall_price": order.get("total"),
            "products": []
        }
        for item in order.get("items", []):
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
            order_data["products"].append(product_data)
        clean_orders.append(order_data)
    return clean_orders
