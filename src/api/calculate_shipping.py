"""Calculate shipping"""

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext
import logging
import os
from typing import Any
from uuid import uuid1

from gre7g_utils import LambdaBase, Cart

# Constants:
LOG = Logger(__name__) if os.getenv("AWS_LAMBDA_FUNCTION_NAME") else logging.getLogger(__name__)


class CalculateShipping(LambdaBase):
    """Calculate shipping"""

    def handler(self, event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
        """Calculate shipping"""
        user_id = self.user_id or self.guest_id

        assert user_id
        assert self.carts_table

        cart = Cart.get(self.carts_table, user_id)
        return {"shipping_cost": self.calc_shipping(cart)}


lambda_handler = CalculateShipping.lambda_handler()
