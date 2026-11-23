"""
Update shopping cart

PUT /api/v1/cart. Replaces the caller's entire cart with the product list supplied by the client.

REQUIRES: CartsRW
"""

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext
import logging
import os
from typing import Any

from database import Cart, Product
from lambda_base import LambdaBase, AuthenticationRequired

# Constants:
LOG = Logger(__name__) if os.getenv("AWS_LAMBDA_FUNCTION_NAME") else logging.getLogger(__name__)


class CartUpdate(LambdaBase):
    """Update shopping cart"""

    AUTH_REQUIRED = AuthenticationRequired.GUEST_OR_USER

    def handler(self, event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
        """Update shopping cart

        Request body: {"products": [<product dict>, ...]}, the complete new cart contents (not a delta).
        Response: {}

        Raises KeyError (400) if "products" or a required product field is missing."""
        # A logged-in identity takes precedence over the guest ID
        user_id = self.user_id or self.guest_id

        assert user_id
        assert self.carts_table

        # Note: the cart is client-written data and is stored as-is. Prices (and anything else) in it are untrusted;
        # place_order re-reads each product from the products table before charging.
        products = [Product.from_dict(product) for product in self.body["products"]]

        # Overwrite the whole cart row
        Cart(user_id, products).put(self.carts_table)

        return {}


lambda_handler = CartUpdate.lambda_handler()
