"""
View shopping cart

GET /api/v1/cart. Returns the cart belonging to the logged-in user or, failing that, the guest.

REQUIRES: CartsRead
"""

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext
import logging
import os
from typing import Any

from database import Cart
from lambda_base import LambdaBase, AuthenticationRequired

# Constants:
LOG = Logger(__name__) if os.getenv("AWS_LAMBDA_FUNCTION_NAME") else logging.getLogger(__name__)


class CartFetch(LambdaBase):
    """View shopping cart"""

    AUTH_REQUIRED = AuthenticationRequired.GUEST_OR_USER

    def handler(self, event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
        """View shopping cart

        Request: Authorization bearer token and/or `x-guest-id` header.
        Response: {"products": [<client product dict>, ...]}; an empty list if there is no cart yet."""
        # A logged-in identity takes precedence over the guest ID
        user_id = self.user_id or self.guest_id

        assert user_id
        assert self.carts_table

        # Cart.get() returns an empty cart rather than raising when no row exists
        cart = Cart.get(self.carts_table, user_id)
        return {"products": cart.to_client_dict()["products"]}


lambda_handler = CartFetch.lambda_handler()
