"""
Confirm order

PUT /api/v1/order/{transaction_id}. Step two of the PayPal checkout flow (see place_order): once the shopper approves
the payment, capture it with PayPal, decrement inventory for physical goods, record the order in our orders table, and
clear the cart. The order contents are taken from PayPal's capture response rather than our cart, so we record exactly
what was paid for.

REQUIRES: AuditRW, CartsRW, ProductsRW, OrdersRW, Gmail
"""

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext
from datetime import datetime
import logging
import os
from paypalserversdk.api_helper import APIHelper
from paypalserversdk.models.item_category import ItemCategory
from typing import Any
from uuid import uuid1

from database import Order, Product, UserId, OrderId
from gmail import send_email_home
from lambda_base import LambdaBase, AuthenticationRequired, AuditLogEvent, CURRENCY

# Constants:
LOG = Logger(__name__) if os.getenv("AWS_LAMBDA_FUNCTION_NAME") else logging.getLogger(__name__)


class ConfirmOrder(LambdaBase):
    """Confirm order"""

    AUTH_REQUIRED = AuthenticationRequired.GUEST_OR_USER

    @staticmethod
    def flush_chaff_from_paypal_response(result: dict[str, Any]) -> None:
        """The result dictionary holds a bunch of stuff we don't really care about. No big deal, but it seems like a
        waste to log it all, so delete it.

        Modifies "result" in place. Also asserts that every capture is COMPLETED, so a partially failed capture aborts
        the confirmation (as a 500) before anything is recorded."""
        result.pop("links", None)
        result.pop("payment_source", None)
        purchase_unit: dict[str, Any]
        for purchase_unit in result.get("purchase_units", []):
            purchase_unit.pop("payee", None)
            captures: list[dict[str, Any]] = purchase_unit.get("payments", {}).get("captures", [])
            for capture in captures:
                assert capture["status"] == "COMPLETED"
                capture.pop("links", None)
                capture.pop("seller_protection", None)

    def process_purchase_units(
        self, user_id: UserId, transaction_id: str, purchase_units: list[dict[str, Any]]
    ) -> Order:
        """Process purchase units from PayPal

        Builds and stores an Order from PayPal's captured purchase units: totals and per-item prices/quantities come
        from PayPal, while the rest of each product record comes from the products table. Physical items are
        decremented from inventory as a side effect.

        Returns the stored Order."""
        assert self.products_table
        assert self.orders_table

        # Create a list of product objects for the order. We also need a list of which products are physical
        # objects. Physical objects have to be tracked in our inventory.
        #
        # Note: Although they're likely equivalent, we will not turn the shopping cart into the order. A malicious
        # actor could have put more stuff into the cart during the checkout process. The PayPal record will show
        # what they actually paid for.
        products = []

        # There's only going to be one purchase unit, I think, but it's a list, so we'll loop over it.
        subtotal = 0.00
        shipping = 0.00
        total = 0.00
        # Fallback order ID; normally overwritten by the reference_id that place_order assigned to the purchase unit
        order_id = OrderId(str(uuid1()))
        for purchase_unit in purchase_units:
            total_money = purchase_unit["amount"]
            order_id = purchase_unit["reference_id"]
            assert total_money["currency_code"] == CURRENCY
            breakdown = total_money["breakdown"]
            subtotal_money = breakdown["item_total"]
            assert subtotal_money["currency_code"] == CURRENCY
            shipping_money = breakdown["shipping"]
            assert shipping_money["currency_code"] == CURRENCY
            subtotal += float(subtotal_money["value"])
            shipping += float(shipping_money["value"])
            total += float(total_money["value"])

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
                    # Atomically decrement stock, but only if there is enough. The payment has already been captured at
                    # this point, so a shortfall does not fail the order; it is logged and the owner is e-mailed to
                    # sort it out (restock or refund) by hand.
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
                                "product_name": item["name"],
                                "stock_quantity": product_listing.quantity,
                                "purchase_quantity": quantity,
                            },
                        )
                        send_email_home(
                            "Inventory Error", f'Insufficient stock of "{item["name"]}" to fulfill order {order_id}'
                        )

                # Reuse the listing as the order line item: quantity now means "quantity purchased", not stock level
                product_listing.quantity = quantity
                product_listing.cost_per = float(unit_amount["value"])
                products.append(product_listing)

        # Create the order object
        notes = ["%s: order placed" % datetime.now().strftime("%m/%d/%Y %H:%M")]
        order = Order(
            user_id,
            products,
            float(subtotal),
            float(shipping),
            float(total),
            transaction_id,
            order_id=order_id,
            notes=notes,
        )
        order.put(self.orders_table)
        return order

    def handler(self, event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
        """Confirm order

        Request: "transaction_id" path parameter (PayPal's order ID returned by place_order) plus Authorization bearer
        token and/or "x-guest-id" header.
        Response: {"order": <client order dict>} with presigned download URLs for any digital goods.

        Any failed assertion on PayPal's response (status not COMPLETED, unexpected currency) surfaces as a 500."""
        # A logged-in identity takes precedence over the guest ID
        user_id = self.user_id or self.guest_id
        transaction_id = self.path_parameters["transaction_id"]  # PayPal's transaction ID, not our ID!

        assert user_id
        assert transaction_id
        assert self.carts_table

        # Capture the payment the shopper approved. "return=representation" asks PayPal to return the full order
        # (purchase units, items, amounts) so we don't need a separate lookup.
        response = self.get_paypal_controller().capture_order({"id": transaction_id, "prefer": "return=representation"})
        result: dict[str, Any] = APIHelper.to_dictionary(response.body)
        assert result["status"] == "COMPLETED"
        self.flush_chaff_from_paypal_response(result)

        # Log what we've received before processing, so there is a record of the payment even if processing fails
        self.audit_log(AuditLogEvent.CONFIRM_ORDER, order=result)

        order = self.process_purchase_units(user_id, transaction_id, result.get("purchase_units", []))
        self.sign_downloads(order)

        # Clear the shopping cart
        self.carts_table.delete_item(Key={"user_id": user_id})

        return {"order": order.to_client_dict()}


lambda_handler = ConfirmOrder.lambda_handler()
