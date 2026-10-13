"""View shopping cart"""

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext
import logging
import os
from typing import Any

from gre7g_utils import LambdaBase, Cart

# Constants:
LOG = Logger(__name__) if os.getenv("AWS_LAMBDA_FUNCTION_NAME") else logging.getLogger(__name__)


class CartFetch(LambdaBase):
    """View shopping cart"""

    def handler(self, event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
        """View shopping cart"""
        LOG.info("handler", extra={"event": event, "user_id": self.user_id, "guest_id": self.guest_id})
        user_id = self.user_id or self.guest_id
        if not user_id:
            raise KeyError()

        assert user_id
        assert self.carts_table

        cart = Cart.get(self.carts_table, user_id)

        products = [
            {
                "name": product.name,
                "quantity": product.quantity,
                "cost_per": product.cost_per,
                "listing_path": product.listing_path,
                "product_id": product.product_id,
            }
            for product in cart.products
        ]
        return {"products": products}


lambda_handler = CartFetch.lambda_handler()
