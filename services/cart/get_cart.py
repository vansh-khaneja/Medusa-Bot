"""
Service for retrieving cart information
"""
import requests


def get_cart(cart_id: str, auth_token: str, x_publishable_api_key: str):
    """
    Retrieve detailed information about a shopping cart.

    Args:
        cart_id: The cart ID
        auth_token: Customer authentication token
        x_publishable_api_key: Store publishable API key

    Returns:
        Dictionary with detailed cart information
    """
    url = f"http://localhost:9000/store/carts/{cart_id}?fields=+items.*"
    headers = {
        "Authorization": f"Bearer {auth_token}",
        "x-publishable-api-key": x_publishable_api_key,
        "Content-Type": "application/json"
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        cart_response = response.json().get("cart", {})

        # Format the cart data
        formatted_cart = {
            "cart_id": cart_response.get("id"),
            "email": cart_response.get("email"),
            "currency_code": cart_response.get("currency_code"),
            "region": {
                "id": cart_response.get("region", {}).get("id"),
                "name": cart_response.get("region", {}).get("name"),
                "currency_code": cart_response.get("region", {}).get("currency_code")
            },
            "totals": {
                "total": cart_response.get("total"),
                "subtotal": cart_response.get("subtotal"),
                "tax_total": cart_response.get("tax_total"),
                "discount_total": cart_response.get("discount_total"),
                "shipping_total": cart_response.get("shipping_total"),
                "item_total": cart_response.get("item_total")
            },
            "items": [],
            "created_at": cart_response.get("created_at"),
            "updated_at": cart_response.get("updated_at")
        }

        # Format items
        for item in cart_response.get("items", []):
            item_data = {
                "id": item.get("id"),
                "product_id": item.get("product_id"),
                "variant_id": item.get("variant_id"),
                "title": item.get("title"),
                "subtitle": item.get("subtitle"),
                "product_title": item.get("product_title"),
                "product_description": item.get("product_description"),
                "product_handle": item.get("product_handle"),
                "variant_sku": item.get("variant_sku"),
                "variant_title": item.get("variant_title"),
                "thumbnail": item.get("thumbnail"),
                "quantity": item.get("quantity"),
                "unit_price": item.get("unit_price"),
                "subtotal": item.get("subtotal"),
                "total": item.get("total"),
                "product_categories": item.get("product", {}).get("categories", [])
            }
            formatted_cart["items"].append(item_data)

        return formatted_cart

    except requests.exceptions.RequestException as e:
        return {"error": f"Failed to fetch cart: {str(e)}"}
