"""Assign order_id"""

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext
import logging
import os
from typing import Any
from uuid import uuid1

from gre7g_utils import LambdaBase

# Constants:
LOG = Logger(__name__) if os.getenv("AWS_LAMBDA_FUNCTION_NAME") else logging.getLogger(__name__)


class AssignOrderId(LambdaBase):
    """Assign order_id"""

    def handler(self, event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
        """Assign order_id"""

        return {"order_id": str(uuid1())}


lambda_handler = AssignOrderId.lambda_handler()
