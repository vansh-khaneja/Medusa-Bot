"""
Service for adding items to cart
"""
import requests


def add_to_cart(cart_id: str, variant_id: str, quantity: int, auth_token: str, x_publishable_api_key: str):
    """
    Add a product variant to the shopping cart.

    Args:
        cart_id: The cart ID
        variant_id: The product variant ID to add
        quantity: Quantity to add
        auth_token: Customer authentication token
        x_publishable_api_key: Store publishable API key

    Returns:
        Dictionary with updated cart information
    """
    url = f"http://localhost:9000/store/carts/{cart_id}/line-items"
    headers = {
        "Authorization": f"Bearer {auth_token}",
        "x-publishable-api-key": x_publishable_api_key,
        "Content-Type": "application/json"
    }

    payload = {
        "variant_id": variant_id,
        "quantity": quantity
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        cart_response = response.json().get("cart", {})

        # Format the cart data (simplified)
        formatted_cart = {
            "cart_id": cart_response.get("id"),
            "email": cart_response.get("email"),
            "currency_code": cart_response.get("currency_code"),
            "totals": {
                "total": cart_response.get("total"),
                "subtotal": cart_response.get("subtotal"),
                "tax_total": cart_response.get("tax_total"),
                "item_total": cart_response.get("item_total")
            },
            "items": [],
            "items_count": len(cart_response.get("items", []))
        }

        # Format items
        for item in cart_response.get("items", []):
            item_data = {
                "id": item.get("id"),
                "product_id": item.get("product_id"),
                "variant_id": item.get("variant_id"),
                "title": item.get("title"),
                "product_title": item.get("product_title"),
                "variant_title": item.get("variant_title"),
                "variant_sku": item.get("variant_sku"),
                "thumbnail": item.get("thumbnail"),
                "quantity": item.get("quantity"),
                "unit_price": item.get("unit_price")
            }
            formatted_cart["items"].append(item_data)

        return formatted_cart

    except requests.exceptions.RequestException as e:
        return {"error": f"Failed to add to cart: {str(e)}"}
