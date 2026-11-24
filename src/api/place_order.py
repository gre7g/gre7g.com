"""
Place order

POST /api/v1/order. Step one of the PayPal checkout flow: builds a PayPal order (intent CAPTURE) from the caller's cart,
using prices from the products table, and creates it with PayPal. The client then has the shopper approve the payment
in the PayPal UI and calls confirm_order with PayPal's order ID to capture the funds. Nothing is written to our tables
here; the cart is left intact until confirm_order succeeds.

REQUIRES: CartsRead, ProductsRead, AuditRW
"""

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext
import logging
import os
from paypalserversdk.api_helper import APIHelper
from paypalserversdk.models.amount_breakdown import AmountBreakdown
from paypalserversdk.models.amount_with_breakdown import AmountWithBreakdown
from paypalserversdk.models.checkout_payment_intent import CheckoutPaymentIntent
from paypalserversdk.models.item import Item
from paypalserversdk.models.item_category import ItemCategory
from paypalserversdk.models.money import Money
from paypalserversdk.models.purchase_unit_request import PurchaseUnitRequest
from paypalserversdk.models.order_request import OrderRequest
from typing import Any
from uuid import uuid1

from audit_log import AuditLogEvent
from database import Cart, Product
from lambda_base import (
    LambdaBase,
    AuthenticationRequired,
    ProductMix,
    AuthException,
    PHYSICAL_SHIPPING,
    CURRENCY,
    OutOfStockException,
)

# Constants:
LOG = Logger(__name__) if os.getenv("AWS_LAMBDA_FUNCTION_NAME") else logging.getLogger(__name__)


class PlaceOrder(LambdaBase):
    """Place order"""

    AUTH_REQUIRED = AuthenticationRequired.GUEST_OR_USER

    def handler(self, event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
        """Place order

        Request: Authorization bearer token and/or `x-guest-id` header; the cart is read from the carts table.
        Response: PayPal's create-order response as a dict (includes the PayPal order "id" the client needs for
        approval and for confirm_order).

        Raises AuthException (401) if a guest tries to buy digital goods."""
        # A logged-in identity takes precedence over the guest ID
        user_id = self.user_id or self.guest_id

        assert user_id
        assert self.carts_table
        assert self.products_table

        cart = Cart.get(self.carts_table, user_id)

        # Create item list
        item_list = []
        products_from_db = []  # Cart contents are unsafe since the user could alter them
        out_of_stock = []
        subtotal_cost = 0.00
        for product in cart.products:
            if product.quantity:
                # WARNING: ITEM COSTS MUST BE LOOKED UP FROM THE PRODUCT DIRECTORY! The user writes the cart data, so
                # these prices would be easy to alter.
                product_listing = Product.get(self.products_table, product.product_id)
                physical_goods = self.physical_item(product_listing.media)

                # Low stock does block the order, but we continue looping in case there are other items that are low too
                if physical_goods and (product_listing.quantity < product.quantity):
                    out_of_stock.append(product.product_id)
                product_listing.quantity = product.quantity
                products_from_db.append(product_listing)

                item = Item(
                    name=product_listing.name,
                    unit_amount=Money(CURRENCY, "%0.2f" % product_listing.cost_per),
                    quantity=str(product.quantity),
                    description=product_listing.short_desc,
                    sku=product_listing.product_id,
                    category=ItemCategory.PHYSICAL_GOODS if physical_goods else ItemCategory.DIGITAL_GOODS,
                )
                item_list.append(item)
                subtotal_cost += product_listing.cost_per * product.quantity

        if out_of_stock:
            raise OutOfStockException(",".join(out_of_stock))

        # Verify that we have enough information to proceed. Digital downloads are tied to a user account, so guests may
        # only buy physical goods.
        mix = self.get_product_mix(products_from_db)
        if mix in [ProductMix.ALL_DIGITAL, ProductMix.MIX_OF_TYPES] and not self.user_id:
            raise AuthException("User must login to purchase digital downloads")

        # Flat-rate shipping if anything physical is in the cart (same rule as calculate_shipping)
        shipping_cost = PHYSICAL_SHIPPING if mix in [ProductMix.ALL_PHYSICAL, ProductMix.MIX_OF_TYPES] else 0.00
        total_cost = subtotal_cost + shipping_cost
        breakdown = AmountBreakdown(Money(CURRENCY, "%0.2f" % subtotal_cost), Money(CURRENCY, "%0.2f" % shipping_cost))

        # A single purchase unit. Its reference_id is a fresh UUID that becomes our order_id when confirm_order reads it
        # back from PayPal's capture response.
        order_request = OrderRequest(
            CheckoutPaymentIntent.CAPTURE,
            [
                PurchaseUnitRequest(
                    AmountWithBreakdown(CURRENCY, "%0.2f" % total_cost, breakdown), str(uuid1()), items=item_list
                )
            ],
        )
        self.audit_log(AuditLogEvent.PLACE_ORDER, order_request=APIHelper.to_dictionary(order_request))

        # Submit order to PayPal. This only creates the order; no money moves until confirm_order captures it.
        response = self.get_paypal_controller().create_order({"body": order_request})

        return APIHelper.to_dictionary(response.body)


lambda_handler = PlaceOrder.lambda_handler()
