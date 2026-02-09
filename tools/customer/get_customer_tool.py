"""
Customer info tool for LangChain
"""
from langchain.tools import tool
from services.customer import get_customer_info as get_customer_service


@tool
def get_customer_tool(auth_token: str, x_publishable_api_key: str) -> str:
    """
    Get the customer's account information including name, email, phone, and addresses.
    Use when user asks about their profile, account info, personal details, or contact information.

    Args:
        auth_token: Customer authentication token
        x_publishable_api_key: Store publishable API key

    Returns:
        Formatted string with customer details
    """
    customer = get_customer_service(auth_token, x_publishable_api_key)

    if "error" in customer:
        return f"❌ {customer['error']}"

    # Format the response
    result = "👤 Your Account Information\n\n"

    # Name
    full_name = f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip()
    if full_name:
        result += f"Name: {full_name}\n"

    # Email
    if customer.get('email'):
        result += f"Email: {customer['email']}\n"

    # Phone
    if customer.get('phone'):
        result += f"Phone: {customer['phone']}\n"

    # Company
    if customer.get('company_name'):
        result += f"Company: {customer['company_name']}\n"

    # Addresses
    addresses = customer.get('addresses', [])
    if addresses:
        result += f"\n📍 Addresses ({len(addresses)}):\n"
        for i, addr in enumerate(addresses, 1):
            result += f"\n{i}. "
            if addr.get('first_name') or addr.get('last_name'):
                result += f"{addr.get('first_name', '')} {addr.get('last_name', '')}".strip() + "\n   "

            address_lines = []
            if addr.get('address_1'):
                address_lines.append(addr['address_1'])
            if addr.get('address_2'):
                address_lines.append(addr['address_2'])
            if addr.get('city'):
                address_lines.append(addr['city'])
            if addr.get('province'):
                address_lines.append(addr['province'])
            if addr.get('postal_code'):
                address_lines.append(addr['postal_code'])
            if addr.get('country_code'):
                address_lines.append(addr['country_code'].upper())

            result += ", ".join(address_lines) + "\n"

            if addr.get('phone'):
                result += f"   Phone: {addr['phone']}\n"
    else:
        result += "\n📍 No addresses saved"

    return result
