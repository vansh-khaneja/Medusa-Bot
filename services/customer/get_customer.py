"""
Service for retrieving customer information
"""
import requests


def get_customer_info(auth_token: str, x_publishable_api_key: str):
    """
    Retrieve information about the authenticated customer.

    Args:
        auth_token: Customer authentication token
        x_publishable_api_key: Store publishable API key

    Returns:
        Dictionary with customer information
    """
    url = "http://localhost:9000/store/customers/me"
    headers = {
        "Authorization": f"Bearer {auth_token}",
        "x-publishable-api-key": x_publishable_api_key,
        "Content-Type": "application/json"
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        customer_response = response.json().get("customer", {})

        # Format the customer data
        formatted_customer = {
            "id": customer_response.get("id"),
            "email": customer_response.get("email"),
            "first_name": customer_response.get("first_name"),
            "last_name": customer_response.get("last_name"),
            "phone": customer_response.get("phone"),
            "company_name": customer_response.get("company_name"),
            "has_account": customer_response.get("has_account"),
            "addresses": customer_response.get("addresses", []),
            "created_at": customer_response.get("created_at"),
            "updated_at": customer_response.get("updated_at")
        }

        return formatted_customer

    except requests.exceptions.RequestException as e:
        return {"error": f"Failed to fetch customer info: {str(e)}"}
