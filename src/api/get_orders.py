"""
Get orders

GET /api/v1/order. Lists all of the logged-in user's orders.

REQUIRES: OrdersRead
"""

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext
from boto3.dynamodb.conditions import Key
import logging
import os
from typing import Any

from database import Order
from lambda_base import LambdaBase, AuthenticationRequired

# Constants:
LOG = Logger(__name__) if os.getenv("AWS_LAMBDA_FUNCTION_NAME") else logging.getLogger(__name__)


class GetOrders(LambdaBase):
    """Get orders"""

    AUTH_REQUIRED = AuthenticationRequired.USER

    def handler(self, event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
        """Get orders

        Request: requires a logged-in user (guests cannot view orders).
        Response: {"orders": [<client order dict>, ...]}. Download links are NOT signed here; fetch an individual order
        via get_order to get usable download URLs."""
        assert self.orders_table
        assert self.user_id

        # user_id is the partition key. A single (unpaginated) query is assumed to return all of a user's orders.
        response = self.orders_table.query(KeyConditionExpression=Key("user_id").eq(self.user_id))

        orders = [Order.from_dict(item).to_client_dict() for item in response["Items"]]
        return {"orders": orders}


lambda_handler = GetOrders.lambda_handler()
