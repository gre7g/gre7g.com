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
        if (self.user_id is None) or (self.guest_id is None) or (self.guest_id == self.user_id):
            raise KeyError()

        cart = Cart.get(self.carts_table, self.guest_id)
        new_product_ids = {product.product_id for product in cart.products}

        for old_product in Cart.get(self.carts_table, self.user_id).products:
            if old_product.product_id not in new_product_ids:
                cart.products.append(old_product)

        cart.user_id = self.user_id
        cart.put(self.carts_table)
        self.carts_table.delete_item(Key={"user_id": self.guest_id})

        return {}


lambda_handler = MergeGuest.lambda_handler()
