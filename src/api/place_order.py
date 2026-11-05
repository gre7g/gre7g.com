"""
Place order

REQUIRES: CartsRead, ProductsRead, AuditsRW
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

from gre7g_utils import (
    LambdaBase,
    Cart,
    AuthenticationRequired,
    ProductMix,
    AuthException,
    PHYSICAL_SHIPPING,
    Product,
    AuditLogEvent,
    CURRENCY,
)

# Constants:
LOG = Logger(__name__) if os.getenv("AWS_LAMBDA_FUNCTION_NAME") else logging.getLogger(__name__)


class PlaceOrder(LambdaBase):
    """Place order"""

    AUTH_REQUIRED = AuthenticationRequired.GUEST_OR_USER

    def handler(self, event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
        """Place order"""
        user_id = self.user_id or self.guest_id

        assert user_id
        assert self.carts_table
        assert self.products_table

        cart = Cart.get(self.carts_table, user_id)

        # Verify that we have enough information to proceed
        mix = self.get_cart_mix(cart)
        if mix in [ProductMix.ALL_DIGITAL, ProductMix.MIX_OF_TYPES] and not self.user_id:
            raise AuthException("User must login to purchase digital downloads")

        # Create item list
        item_list = []
        out_of_stock = []
        subtotal_cost = 0.00
        for product in cart.products:
            # WARNING: ITEM COSTS MUST BE LOOKED UP FROM THE PRODUCT DIRECTORY! The user writes the cart data, so these
            # prices would be easy to alter.
            product_listing = Product.get(self.products_table, product.product_id)
            physical_goods = product_listing.media in ["paperback", "jewelry"]
            if physical_goods and (product_listing.quantity < product.quantity):
                out_of_stock.append(product.product_id)
            else:
                item = Item(
                    name=product_listing.name,
                    unit_amount=Money(CURRENCY, "%0.2f" % product_listing.cost_per),
                    quantity=str(product.quantity),
                    description=product_listing.description,
                    sku=product_listing.product_id,
                    category=ItemCategory.PHYSICAL_GOODS if physical_goods else ItemCategory.DIGITAL_GOODS,
                )
                item_list.append(item)
                subtotal_cost += product_listing.cost_per * product.quantity

        if out_of_stock:
            return {"status": "cannot_fulfill", "out_of_stock": out_of_stock}

        shipping_cost = PHYSICAL_SHIPPING if mix in [ProductMix.ALL_PHYSICAL, ProductMix.MIX_OF_TYPES] else 0.00
        total_cost = subtotal_cost + shipping_cost
        breakdown = AmountBreakdown(Money(CURRENCY, "%0.2f" % subtotal_cost), Money(CURRENCY, "%0.2f" % shipping_cost))

        order_request = OrderRequest(
            CheckoutPaymentIntent.CAPTURE,
            [
                PurchaseUnitRequest(
                    AmountWithBreakdown(CURRENCY, "%0.2f" % total_cost, breakdown), str(uuid1()), items=item_list
                )
            ],
        )
        self.audit_log(AuditLogEvent.PLACE_ORDER, order_request=APIHelper.to_dictionary(order_request))

        # Submit order to PayPal
        response = self.get_paypal_controller().create_order({"body": order_request})

        return APIHelper.to_dictionary(response.body)


lambda_handler = PlaceOrder.lambda_handler()
