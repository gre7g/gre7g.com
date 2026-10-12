"""Update shopping cart"""

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext
import json
import logging
import os
from typing import Any

from gre7g_utils import LambdaBase, Cart

# Constants:
LOG = Logger(__name__) if os.getenv("AWS_LAMBDA_FUNCTION_NAME") else logging.getLogger(__name__)


class CartUpdate(LambdaBase):
    """Update shopping cart"""

    def handler(self, event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
        """Update shopping cart"""
        user_id = self.user_id or self.guest_id

        assert user_id
        assert self.carts_table

        body = json.loads(event["body"])
        products = body["products"]

        Cart(user_id, products).put(self.carts_table)

        return {}


lambda_handler = CartUpdate.lambda_handler()
