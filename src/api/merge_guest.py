"""Merge guest authorization"""

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext
import logging
import os
from typing import Any

from gre7g_utils import LambdaBase, Cart, UserId

# Constants:
LOG = Logger(__name__) if os.getenv("AWS_LAMBDA_FUNCTION_NAME") else logging.getLogger(__name__)


class MergeGuest(LambdaBase):
    """Merge guest authorization"""

    def handler(self, event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
        """Merge guest authorization"""
        assert self.carts_table

        cart = Cart.get(self.carts_table, self.user_id)
        new_product_ids = {product.product_id for product in cart.products}

        for product in Cart.get(self.carts_table, self.guest_id).products:
            if product.product_id not in new_product_ids:
                cart.products.append(product)

        cart.put(self.carts_table)

        return {}


lambda_handler = MergeGuest.lambda_handler()
