"""Confirm order"""

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext
from datetime import datetime
import logging
import os
from paypalserversdk.api_helper import APIHelper
from paypalserversdk.configuration import Environment
from paypalserversdk.http.auth.o_auth_2 import ClientCredentialsAuthCredentials
from paypalserversdk.logging.configuration.api_logging_configuration import (
    LoggingConfiguration,
    RequestLoggingConfiguration,
    ResponseLoggingConfiguration,
)
from paypalserversdk.models.amount_breakdown import AmountBreakdown
from paypalserversdk.models.amount_with_breakdown import AmountWithBreakdown
from paypalserversdk.models.checkout_payment_intent import CheckoutPaymentIntent
from paypalserversdk.controllers.orders_controller import OrdersController
from paypalserversdk.models.item import Item
from paypalserversdk.models.item_category import ItemCategory
from paypalserversdk.models.money import Money
from paypalserversdk.models.purchase_unit_request import PurchaseUnitRequest
from paypalserversdk.models.order_request import OrderRequest
from paypalserversdk.paypal_serversdk_client import PaypalServersdkClient
from typing import Any

from gre7g_utils import (
    LambdaBase,
    Cart,
    AuthenticationRequired,
    ProductMix,
    AuthException,
    PHYSICAL_SHIPPING,
    Order,
    UserId,
    Product,
    ProductStatus,
)

# Constants:
LOG = Logger(__name__) if os.getenv("AWS_LAMBDA_FUNCTION_NAME") else logging.getLogger(__name__)
CURRENCY = "USD"


class ConfirmOrder(LambdaBase):
    """Confirm order"""

    AUTH_REQUIRED = AuthenticationRequired.GUEST_OR_USER

    # def convert_cart_to_order(self, user_id: UserId, cart: Cart, mix: ProductMix) -> tuple[Order, dict]:
    #     """Convert the shopping cart into an order (our format and PayPal's)"""
    #     assert self.products_table
    #
    #     products = []
    #     item_list = []
    #     subtotal_cost = 0.00
    #     for product in cart.products:
    #         # WARNING: ITEM COSTS MUST BE LOOKED UP FROM THE PRODUCT DIRECTORY! The user writes the cart data, so these
    #         # prices would be easy to change.
    #         product_listing = Product.get(self.products_table, product.product_id)
    #         physical_goods = product_listing.media in ["paperback", "jewelry"]
    #         subtotal_cost += product_listing.cost_per * product.quantity
    #
    #         # Product object for our Order object
    #         product_listing.quantity = product.quantity
    #         product_listing.status = ProductStatus.ORDERED if physical_goods else ProductStatus.AVAILABLE
    #         products.append(product_listing)
    #
    #         # Item object for PayPal's item list
    #         item = Item(
    #             name=product_listing.name,
    #             unit_amount=Money(CURRENCY, product_listing.cost_per),
    #             quantity=str(product.quantity),
    #             description=product_listing.description,
    #             sku=product_listing.product_id,
    #             category=ItemCategory.PHYSICAL_GOODS if physical_goods else ItemCategory.DIGITAL_GOODS,
    #         )
    #         item_list.append(item)
    #
    #     shipping_cost = PHYSICAL_SHIPPING if mix in [ProductMix.ALL_PHYSICAL, ProductMix.MIX_OF_TYPES] else 0.00
    #     total_cost = subtotal_cost + shipping_cost
    #     breakdown = AmountBreakdown(Money(CURRENCY, subtotal_cost), Money(CURRENCY, shipping_cost))
    #     notes = ["%s: order placed" % datetime.now().strftime("%m/%d/%Y %H:%M")]
    #
    #     order = Order(user_id, products, subtotal_cost, shipping_cost, total_cost, notes=notes)
    #     order_dict = {
    #         "body": OrderRequest(
    #             CheckoutPaymentIntent.CAPTURE,
    #             [
    #                 PurchaseUnitRequest(
    #                     AmountWithBreakdown(CURRENCY, total_cost, breakdown), order.order_id, items=item_list
    #                 )
    #             ],
    #         )
    #     }
    #
    #     return order, order_dict

    def handler(self, event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
        """Confirm order"""
        order_id = self.path_parameters["order_id"]
        result = self.get_paypal_controller().capture_order({"id": order_id, "prefer": "return=representation"})
        from pprint import pprint

        pprint(APIHelper.to_dictionary(result.body))
        a = {
            "create_time": "2026-11-01T19:55:45Z",
            "id": "9VW41488W5981982P",
            "intent": "CAPTURE",
            "links": [...],
            "payer": {
                "address": {"country_code": "US"},
                "email_address": "sb-f6pza23450164@personal.example.com",
                "name": {"given_name": "John", "surname": "Doe"},
                "payer_id": "NXC8NXJ92ZM36",
            },
            "payment_source": {...},
            "purchase_units": [
                {
                    "amount": {
                        "breakdown": {
                            "handling": {...},
                            "insurance": {...},
                            "item_total": {"currency_code": "USD", "value": "13.99"},
                            "shipping": {"currency_code": "USD", "value": "5.99"},
                            "shipping_discount": {...},
                        },
                        "currency_code": "USD",
                        "value": "19.98",
                    },
                    "description": "IGNORE THIS STRING. IT IS NOT RELIABLE.",
                    "items": [
                        {
                            "category": "PHYSICAL_GOODS",
                            "description": "<p>220 pages, Illustrated</p>",
                            "name": "Skeleton Crew − paperback",
                            "quantity": "1",
                            "sku": "kc1-paperback",
                            "tax": {...},
                            "unit_amount": {"currency_code": "USD", "value": "13.99"},
                        }
                    ],
                    "payee": {...},
                    "payments": {
                        "captures": [
                            {
                                "amount": {"currency_code": "USD", "value": "19.98"},
                                "create_time": "2026-11-01T19:55:54Z",
                                "disbursement_mode": "INSTANT",
                                "final_capture": True,
                                "id": "1M723936WL388890M",
                                "links": [...],
                                "seller_protection": {...},
                                "seller_receivable_breakdown": {
                                    "gross_amount": {"currency_code": "USD", "value": "19.98"},
                                    "net_amount": {"currency_code": "USD", "value": "18.79"},
                                    "paypal_fee": {"currency_code": "USD", "value": "1.19"},
                                },
                                "status": "COMPLETED",
                                "update_time": "2026-11-01T19:55:54Z",
                            }
                        ]
                    },
                    "reference_id": "3909bacad62e11f1b2a964d69adcd141",
                    "shipping": {
                        "address": {
                            "address_line_1": "1 Main St",
                            "admin_area_1": "CA",
                            "admin_area_2": "San Jose",
                            "country_code": "US",
                            "postal_code": "95131",
                        },
                        "name": {"full_name": "John Doe"},
                    },
                }
            ],
            "status": "COMPLETED",
            "update_time": "2026-11-01T19:55:54Z",
        }
        return {}

        # user_id = self.user_id or self.guest_id
        #
        # assert user_id
        # assert self.carts_table
        #
        # cart = Cart.get(self.carts_table, user_id)
        #
        # # Verify that we have enough information to proceed
        # mix = self.get_cart_mix(cart)
        # if mix in [ProductMix.ALL_DIGITAL, ProductMix.MIX_OF_TYPES] and not self.user_id:
        #     raise AuthException("User must login to purchase digital downloads")
        #
        # # Create order objects
        # order, order_dict = self.convert_cart_to_order(user_id, cart, mix)
        #
        # # Submit order to PayPal
        # result = self.get_paypal_controller().create_order(order_dict)
        # return APIHelper.to_dictionary(result.body)


lambda_handler = ConfirmOrder.lambda_handler()
