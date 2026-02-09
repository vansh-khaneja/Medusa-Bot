"""
Service for retrieving product details and variants
"""
import requests


def get_product_by_id(product_id: str, x_publishable_api_key: str, region_id: str = None):
    """
    Retrieve detailed information about a product including all variants with prices.

    Args:
        product_id: The product ID
        x_publishable_api_key: Store publishable API key
        region_id: Optional region ID for pricing context

    Returns:
        Dictionary with product information including variants with calculated prices
    """
    # Add query parameters to get calculated prices
    params = {
        "fields": "+variants.calculated_price"  # Use + prefix to include calculated_price
    }

    # Region ID is required for calculated prices
    # Default to a known region if not provided (you may want to fetch this dynamically)
    if not region_id:
        region_id = "reg_01KGVN5AJEM92NJZDD5WN8GRN1"  # Default region (Europe/USD)

    params["region_id"] = region_id

    url = f"http://localhost:9000/store/products/{product_id}"
    headers = {
        "x-publishable-api-key": x_publishable_api_key,
        "Content-Type": "application/json"
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        product_response = response.json().get("product", {})

        # Format the product data
        formatted_product = {
            "id": product_response.get("id"),
            "title": product_response.get("title"),
            "description": product_response.get("description"),
            "handle": product_response.get("handle"),
            "thumbnail": product_response.get("thumbnail"),
            "options": [],
            "variants": [],
            "images": []
        }

        # Format options (Size, Color, etc.)
        for option in product_response.get("options", []):
            formatted_option = {
                "id": option.get("id"),
                "title": option.get("title"),
                "values": [val.get("value") for val in option.get("values", [])]
            }
            formatted_product["options"].append(formatted_option)

        # Format variants
        for variant in product_response.get("variants", []):
            formatted_variant = {
                "id": variant.get("id"),
                "title": variant.get("title"),
                "sku": variant.get("sku"),
                "options": {}
            }

            # Extract option values (Size: M, Color: Black, etc.)
            for opt in variant.get("options", []):
                option_title = opt.get("option", {}).get("title")
                option_value = opt.get("value")
                if option_title and option_value:
                    formatted_variant["options"][option_title] = option_value

            # Extract price information from calculated_price
            calculated_price = variant.get("calculated_price", {})
            if calculated_price:
                formatted_variant["price"] = {
                    "amount": calculated_price.get("calculated_amount"),
                    "amount_with_tax": calculated_price.get("calculated_amount_with_tax"),
                    "currency_code": calculated_price.get("currency_code"),
                    "original_amount": calculated_price.get("original_amount")
                }

            formatted_product["variants"].append(formatted_variant)

        # Format images
        for image in product_response.get("images", []):
            formatted_product["images"].append({
                "id": image.get("id"),
                "url": image.get("url"),
                "rank": image.get("rank")
            })

        return formatted_product

    except requests.exceptions.RequestException as e:
        return {"error": f"Failed to fetch product: {str(e)}"}
