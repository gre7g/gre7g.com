"""
Get order

REQUIRES: OrdersRead
"""

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext
import logging
import os
from typing import Any

from database import Order
from lambda_base import LambdaBase, AuthenticationRequired

# Constants:
LOG = Logger(__name__) if os.getenv("AWS_LAMBDA_FUNCTION_NAME") else logging.getLogger(__name__)


class GetOrder(LambdaBase):
    """Get order"""

    AUTH_REQUIRED = AuthenticationRequired.USER

    def handler(self, event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
        """Get order"""
        assert self.orders_table
        assert self.user_id

        order = Order.get(self.orders_table, self.user_id, self.path_parameters["order_id"])
        self.sign_downloads(order)

        return {"order": order.to_client_dict()}


lambda_handler = GetOrder.lambda_handler()
