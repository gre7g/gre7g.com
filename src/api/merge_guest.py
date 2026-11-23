"""
Merge guest authorization

PUT /api/v1/guest. Called right after a guest logs in: folds the guest cart into the user's own cart, then deletes the
guest cart so the guest ID is no longer needed.

REQUIRES: CartsRW, AuditRW
"""

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext
import logging
import os
from typing import Any

from audit_log import AuditLogEvent
from database import Cart
from lambda_base import LambdaBase, AuthenticationRequired

# Constants:
LOG = Logger(__name__) if os.getenv("AWS_LAMBDA_FUNCTION_NAME") else logging.getLogger(__name__)


class MergeGuest(LambdaBase):
    """Merge guest authorization"""

    AUTH_REQUIRED = AuthenticationRequired.GUEST_AND_USER

    def handler(self, event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
        """Merge guest authorization

        Request: both an Authorization bearer token and an `x-guest-id` header.
        Response: {"products": [<client product dict>, ...]}, the merged cart.

        Raises KeyError (400) if the guest ID is the same as the user ID."""
        assert self.carts_table
        assert self.user_id
        # Merging a cart into itself would end with the delete below wiping the user's cart
        if self.guest_id == self.user_id:
            raise KeyError()
        assert self.guest_id

        # Start from the guest cart, since it reflects what the shopper was doing just before logging in
        cart = Cart.get(self.carts_table, self.guest_id)
        self.audit_log(AuditLogEvent.CART_MERGE, cart=cart.to_client_dict())
        new_product_ids = {product.product_id for product in cart.products}

        # Add back items from the user's previously saved cart. Where a product is in both carts, the guest cart's entry
        # (and quantity) wins; quantities are not summed.
        for old_product in Cart.get(self.carts_table, self.user_id).products:
            if old_product.product_id not in new_product_ids:
                cart.products.append(old_product)

        # Re-home the merged cart under the user ID and drop the guest cart
        cart.user_id = self.user_id
        cart.put(self.carts_table)
        self.carts_table.delete_item(Key={"user_id": self.guest_id})

        return {"products": cart.to_client_dict()["products"]}


lambda_handler = MergeGuest.lambda_handler()
