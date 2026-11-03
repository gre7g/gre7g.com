"""Calculate shipping"""

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext
import logging
import os
from typing import Any

from gre7g_utils import LambdaBase, Cart, PHYSICAL_SHIPPING, ProductMix

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
        mix = self.get_cart_mix(cart)

        shipping_cost = PHYSICAL_SHIPPING if mix in [ProductMix.ALL_PHYSICAL, ProductMix.MIX_OF_TYPES] else 0.00
        if self.user_id:
            user_status = "logged_in"
        else:
            user_status = "must_log_in" if mix in [ProductMix.ALL_DIGITAL, ProductMix.MIX_OF_TYPES] else "may_log_in"

        return {"shipping_cost": shipping_cost, "user_status": user_status}


lambda_handler = CalculateShipping.lambda_handler()
