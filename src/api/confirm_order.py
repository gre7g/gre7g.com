"""Confirm order"""

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext
from datetime import datetime
import logging
import os
from paypalserversdk.api_helper import APIHelper
from paypalserversdk.models.item_category import ItemCategory
from typing import Any

from gre7g_utils import LambdaBase, AuthenticationRequired, Order, Product, AuditLogEvent, CURRENCY

# Constants:
LOG = Logger(__name__) if os.getenv("AWS_LAMBDA_FUNCTION_NAME") else logging.getLogger(__name__)


class ConfirmOrder(LambdaBase):
    """Confirm order"""

    AUTH_REQUIRED = AuthenticationRequired.GUEST_OR_USER

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

            for item in purchase_unit["items"]:
                # We will take the product objects from the products table, but keep a couple things from the PayPal
                # record, namely quantity and cost_per. Although it's unlikely that the price would change between
                # checkout and order confirmation, it is possible, and we want to record what the user paid, not the
                # latest price.
                product_id = item["sku"]
                product_listing = Product.get(self.products_table, product_id)
                quantity = int(item["quantity"])
                unit_amount = item["unit_amount"]
                assert unit_amount["currency_code"] == CURRENCY

                if item["category"] == ItemCategory.PHYSICAL_GOODS:
                    try:
                        self.products_table.update_item(
                            Key={"product_id": product_id},
                            UpdateExpression="SET quantity = quantity - :purchased",
                            ConditionExpression="quantity >= :purchased",
                            ExpressionAttributeValues={":purchased": quantity},
                        )
                    except self.products_table.meta.client.exceptions.ConditionalCheckFailedException:
                        LOG.error(
                            "Insufficient stock",
                            extra={
                                "product_id": product_id,
                                "name": item["name"],
                                "stock_quantity": product_listing.quantity,
                                "purchase_quantity": quantity,
                            },
                        )
                        # TODO: email an admin, this is important!

                product_listing.quantity = quantity
                product_listing.cost_per = float(unit_amount["value"])
                products.append(product_listing)

            # Create the order object
            total = purchase_unit["amount"]
            assert total["currency_code"] == CURRENCY
            breakdown = total["breakdown"]
            subtotal = breakdown["item_total"]
            assert subtotal["currency_code"] == CURRENCY
            shipping = breakdown["shipping"]
            assert shipping["currency_code"] == CURRENCY
            notes = ["%s: order placed" % datetime.now().strftime("%m/%d/%Y %H:%M")]
            order = Order(
                user_id,
                products,
                float(subtotal["value"]),
                float(shipping["value"]),
                float(total["value"]),
                order_id=purchase_unit["reference_id"],
                notes=notes,
            )
            order.put(self.orders_table)

        # Clear the shopping cart
        self.carts_table.delete_item(Key={"user_id": user_id})

        return {}


lambda_handler = ConfirmOrder.lambda_handler()
