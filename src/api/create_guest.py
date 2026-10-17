"""Create a guest authorization"""

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext
import logging
import os
from typing import Any
from uuid import uuid1

from gre7g_lib.gre7g_utils import LambdaBase

# Constants:
LOG = Logger(__name__) if os.getenv("AWS_LAMBDA_FUNCTION_NAME") else logging.getLogger(__name__)


class CreateGuest(LambdaBase):
    """Create a guest authorization"""

    def handler(self, event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
        """Create a guest authorization"""

        return {"auth_token": uuid1().hex}


lambda_handler = CreateGuest.lambda_handler()
