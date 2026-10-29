Note: Google's AI suggested the following. It did not come directly from PayPal.com and should be treated with 
suspicion.

To submit an order with line items and shipping details programmatically for PayPal Checkout, you use the PayPal Orders
v2 API to create and capture an order.

The primary integration steps involve setting up your server, passing purchase details in the payload, and managing the
buyer's shipping preference.

1. Choose a Shipping Preference

When creating an order via the PayPal Orders API, you define how shipping addresses are handled using the
shipping_preference parameter:

- GET_FROM_FILE: Displays the shipping address from the buyer's PayPal profile on the review page, allowing them to
- change it.

- SET_PROVIDED_ADDRESS: Locks the shipping address to the one you pass in the request (prevents changes on PayPal's
- review page).

- NO_SHIPPING: Hides shipping information entirely (useful for digital goods or services).

2. Make the Create Order API Request

Send a POST request to the PayPal Standard Checkout API endpoint (https://api-m.sandbox.paypal.com/v2/checkout/orders
for sandbox testing, or the live endpoint for production).

Include your itemized breakdown (item names, quantities, unit prices), shipping costs, tax, and the shipping_preference
inside the payload:

```json
{
    "intent": "CAPTURE",
    "purchase_units": [
        {
            "amount": {
                "currency_code": "USD",
                "value": "115.00",
                "breakdown": {
                    "item_total": {
                        "currency_code": "USD",
                        "value": "100.00"
                    },
                    "shipping": {
                        "currency_code": "USD",
                        "value": "10.00"
                    },
                    "tax_total": {
                        "currency_code": "USD",
                        "value": "5.00"
                    }
                }
            },
            "items": [
                {
                    "name": "First Item Name",
                    "quantity": "1",
                    "unit_amount": {
                        "currency_code": "USD",
                        "value": "100.00"
                    }
                }
            ],
            "shipping": {
                "options": [
                    {
                        "id": "SHIP_OPT_1",
                        "label": "Standard Shipping",
                        "type": "SHIPPING",
                        "selected": true,
                        "amount": {
                            "currency_code": "USD",
                            "value": "10.00"
                        }
                    }
                ]
            }
        }
    ],
    "payment_source": {
        "paypal": {
            "experience_context": {
                "user_action": "PAY_NOW",
                "shipping_preference": "GET_FROM_FILE",
                "return_url": "https://example.com/returnUrl",
                "cancel_url": "https://example.com/cancelUrl"
            }
        }
    }
}
```

3. Handle the Buyer Review and Capture

    1. Redirect the Payer: Direct the buyer to the PayPal review page returned in the order response so they can log in,
       verify the items and shipping address, and approve the payment.

    2. Capture the Order: Once the buyer approves the transaction and returns to your return_url, trigger an
       ordersCapture request on your backend server using the ORDER-ID to finalize and collect the funds.

    3. Set Up Shipment Tracking: After capturing payment and shipping the physical goods, submit tracking information
       via PayPal's shipment tracking API to maintain seller protection.

To submit an order using the PayPal REST API (v2), you will orchestrate the flow between your backend server, your
frontend UI, and the PayPal API endpoints.

Here is the step-by-step implementation guide using raw HTTP requests.

Step 1: Generate an Access Token

Before sending any order data, your backend must authenticate using your client ID and secret via Basic Auth to get a
temporary OAuth 2.0 access token.

- Endpoint: POST https://paypal.com
- Headers:
- Authorization: Basic <Base64_Encoded_Client_ID:Secret>
- Content-Type: application/x-www-form-urlencoded
- Body: grant_type=client_credentials

Step 2: Create the Order (Backend)

Once you have the token, create the order payload. To include items and shipping properly, ensure that:

1. item_total, shipping, and tax_total in the breakdown object add up exactly to the overall amount.value.

2. The sum of all individual item quantities multiplied by their unit prices equals item_total.

    - Endpoint: POST https://paypal.com
    - Headers:
    - Authorization: Bearer <Your_Access_Token>
    - Content-Type: application/json

Request Body

```json
{
    "intent": "CAPTURE",
    "purchase_units": [
        {
            "reference_id": "PU_12345",
            "amount": {
                "currency_code": "USD",
                "value": "115.00",
                "breakdown": {
                    "item_total": {
                        "currency_code": "USD",
                        "value": "100.00"
                    },
                    "shipping": {
                        "currency_code": "USD",
                        "value": "10.00"
                    },
                    "tax_total": {
                        "currency_code": "USD",
                        "value": "5.00"
                    }
                }
            },
            "items": [
                {
                    "name": "Wireless Headphones",
                    "sku": "HP-9000",
                    "quantity": "2",
                    "unit_amount": {
                        "currency_code": "USD",
                        "value": "50.00"
                    },
                    "category": "PHYSICAL_GOODS"
                }
            ],
            "shipping": {
                "name": {
                    "full_name": "John Doe"
                },
                "address": {
                    "address_line_1": "123 Main St",
                    "admin_area_2": "San Jose",
                    "admin_area_1": "CA",
                    "postal_code": "95131",
                    "country_code": "US"
                }
            }
        }
    ],
    "payment_source": {
        "paypal": {
            "experience_context": {
                "payment_method_preference": "IMMEDIATE_PAYMENT_REQUIRED",
                "shipping_preference": "SET_PROVIDED_ADDRESS",
                "user_action": "PAY_NOW",
                "return_url": "https://yourwebsite.com",
                "cancel_url": "https://yourwebsite.com"
            }
        }
    }
}
```

Note on shipping_preference: Using "SET_PROVIDED_ADDRESS" forces PayPal to use the address you passed above and prevents
the user from changing it on the PayPal screen.

Response Look for the Checkout Link

PayPal will respond with an order ID and a list of links. Look for the rel: "payer_action" or rel: "approve" link to
redirect your customer:

```json
{
  "links": [
    {
      "href": "https://paypal.com",
      "rel": "payer_action",
      "method": "GET"
    }
  ]
}
```

Step 3: Capture the Payment (Backend)

After the buyer logs into PayPal and approves the payment, they will be redirected to your specified return_url. PayPal
will append a token query parameter to the URL (which matches your Order ID).

Your backend must immediately execute the capture call using that ID to actually withdraw the funds.

• Endpoint: POST https://paypal.com{id}/capture
• Headers:
• Authorization: Bearer <Your_Access_Token>
• Content-Type: application/json
• Body: {} (Empty JSON payload)

If successful, the response status will show "STATUS": "COMPLETED", indicating that the transaction is settled and you
can safely fulfill the order.
