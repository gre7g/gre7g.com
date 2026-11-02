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
    ProductStatus,AuditLogEvent, CURRENCY
)

# Constants:
LOG = Logger(__name__) if os.getenv("AWS_LAMBDA_FUNCTION_NAME") else logging.getLogger(__name__)


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
        user_id = self.user_id or self.guest_id
        order_id = self.path_parameters["order_id"]

        assert user_id
        assert order_id
        assert self.products_table
        assert self.orders_table

        # Fetch order from PayPal
        response = self.get_paypal_controller().capture_order({"id": order_id, "prefer": "return=representation"})
        result: dict[str, Any] = APIHelper.to_dictionary(response.body)
        assert result["status"] == "COMPLETED"

        # The result dictionary holds a bunch of stuff we don't really care about. No big deal, but it seems like a
        # waste to log it all, so I'll take a moment to delete it.
        result.pop("links", None)
        result.pop("payment_source", None)
        purchase_unit: list[dict[str, Any]]
        for purchase_unit in result.get("purchase_units", []):
            purchase_unit.pop("payee", None)
            captures: list[dict[str, Any]] = purchase_unit.get("payments", {}).get("captures", [])
            for capture in captures:
                assert capture["status"] == "COMPLETED"
                capture.pop("links", None)
                capture.pop("seller_protection", None)

        # Log what we've received
        self.audit_log(AuditLogEvent.CONFIRM_ORDER, order=result)

        # There's only going to be one purchase unit, I think, but it's a list, so we'll loop over it.
        for purchase_unit in result.get("purchase_units", []):
            # Create a list of product objects for the order. We also need a list of which products are physical
            # objects. Physical objects have to be tracked in our inventory.
            #
            # Note: Although they're likely equivalent, we will not turn the shopping cart into the order. A malicious
            # actor could have put more stuff into the cart during the checkout process. The PayPal record will show
            # what they actually paid for.
            products = []
            physical_product_ids = []

            for item in purchase_unit["items"]:
                # We will take the product objects from the products table, but keep a couple things from the PayPal
                # record, namely quantity and cost_per. Although it's unlikely that the price would change between
                # checkout and order confirmation, it is possible, and we want to record what the user paid, not the
                # latest price.
                product_listing = Product.get(self.products_table, item["sku"])

                if item["category"] == ItemCategory.PHYSICAL_GOODS:
                    physical_product_ids.append(item["sku"])

                product_listing.quantity = int(item["quantity"])
                unit_amount = item["unit_amount"]
                assert unit_amount["currency_code"] == CURRENCY
                product_listing.cost_per = float(unit_amount["value"])
                products.append(product)

            # If there were any physical items, update the quantities in the database
            if physical_product_ids:
                # In a transaction, find all the records in self.products_table where {"product_id": product_id} and update quantity-=1, rolling back if any fail

            amount = purchase_unit["amount"]
            assert amount["currency_code"] == CURRENCY
            breakdown = amount["breakdown"]
            subtotal = breakdown["item_total"]
            assert subtotal["currency_code"] == CURRENCY
            shipping = breakdown["shipping"]
            assert shipping["currency_code"] == CURRENCY
            notes = ["%s: order placed" % datetime.now().strftime("%m/%d/%Y %H:%M")]
            order = Order(user_id, products, float(subtotal["value"]), float(shipping["value"]), float(amount["value"]), order_id=purchase_unit["reference_id"], notes=notes)
            order.put(self.orders_table)
        a = {
            "purchase_units": [
                {
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
                }
            ],
        }
        return {}

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
