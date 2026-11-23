"""
Get order

GET /api/v1/order/{order_id}. Returns one of the logged-in user's orders, with fresh download links.

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
        """Get order

        Request: "order_id" path parameter; requires a logged-in user (guests cannot view orders).
        Response: {"order": <client order dict>} with each download replaced by a time-limited presigned S3 URL.

        Raises KeyError (400) if the order does not exist for this user."""
        assert self.orders_table
        assert self.user_id

        # The table key includes user_id, so a user can only ever fetch their own orders
        order = Order.get(self.orders_table, self.user_id, self.path_parameters["order_id"])
        # Signed URLs expire, so they are regenerated on every fetch rather than stored
        self.sign_downloads(order)

        return {"order": order.to_client_dict()}


lambda_handler = GetOrder.lambda_handler()
