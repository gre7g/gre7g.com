"""Get orders"""

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext
from boto3.dynamodb.conditions import Key
import logging
import os
from typing import Any

from gre7g_utils import LambdaBase, Order, AuthenticationRequired

# Constants:
LOG = Logger(__name__) if os.getenv("AWS_LAMBDA_FUNCTION_NAME") else logging.getLogger(__name__)


class GetOrders(LambdaBase):
    """Get orders"""

    AUTH_REQUIRED = AuthenticationRequired.USER

    def handler(self, event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
        """Get orders"""
        assert self.orders_table
        assert self.user_id

        response = self.orders_table.query(KeyConditionExpression=Key("user_id").eq(self.user_id))

        orders = [Order.from_dict(item).to_client_dict() for item in response["Items"]]
        return {"orders": orders}


lambda_handler = GetOrders.lambda_handler()
