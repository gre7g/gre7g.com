"""View shopping cart"""

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext
import logging
import os
from typing import Any

from gre7g_lib.gre7g_utils import LambdaBase, Cart, AuthenticationRequired

# Constants:
LOG = Logger(__name__) if os.getenv("AWS_LAMBDA_FUNCTION_NAME") else logging.getLogger(__name__)


class CartFetch(LambdaBase):
    """View shopping cart"""

    AUTH_REQUIRED = AuthenticationRequired.GUEST_OR_USER

    def handler(self, event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
        """View shopping cart"""
        user_id = self.user_id or self.guest_id

        assert user_id
        assert self.carts_table

        cart = Cart.get(self.carts_table, user_id)
        return {"products": cart.to_client_dict()["products"]}


lambda_handler = CartFetch.lambda_handler()
