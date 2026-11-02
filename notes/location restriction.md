```python
import requests

PAYPAL_API_URL = "https://paypal.com" # Use ://paypal.com for production

def validate_and_capture_order(order_id, access_token):
    # 1. Fetch the latest order details from PayPal
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    order_response = requests.get(f"{PAYPAL_API_URL}/v2/checkout/orders/{order_id}", headers=headers)
    order_data = order_response.json()
    
    # 2. Check if the order requires physical shipping
    has_physical_items = False
    for purchase_unit in order_data.get("purchase_units", []):
        items = purchase_unit.get("items", [])
        for item in items:
            # PayPal item categories: 'PHYSICAL', 'DIGITAL', or 'DONATION'
            if item.get("category") == "PHYSICAL":
                has_physical_items = True
                break

    # 3. If it has physical items, enforce the US-only shipping rule
    if has_physical_items:
        for purchase_unit in order_data.get("purchase_units", []):
            shipping = purchase_unit.get("shipping", {})
            address = shipping.get("address", {})
            country_code = address.get("country_code")
            
            if country_code != "US":
                # Terminate before capturing money
                return {
                    "status": "FAILED",
                    "error": "International shipping is not supported for physical items."
                }

    # 4. If it's digital-only, or physical and shipping to US, proceed to capture
    capture_response = requests.post(
        f"{PAYPAL_API_URL}/v2/checkout/orders/{order_id}/capture", 
        headers=headers
    )
    
    return capture_response.json()
```
