"""
Create a guest authorization

POST /api/v1/guest. Gives an anonymous visitor a random guest ID. The client sends it back in the `x-guest-id` header
so it can keep a shopping cart before logging in (see merge_guest for what happens when they do log in).

REQUIRES: none
"""

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext
import logging
import os
from typing import Any
from uuid import uuid1

from lambda_base import LambdaBase

# Constants:
LOG = Logger(__name__) if os.getenv("AWS_LAMBDA_FUNCTION_NAME") else logging.getLogger(__name__)


class CreateGuest(LambdaBase):
    """Create a guest authorization

    The guest ID is an unsigned bearer value: it is never stored server-side, so possession of the ID is the only thing
    that ties a visitor to their guest cart."""

    def handler(self, event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
        """Create a guest authorization

        Request: no inputs.
        Response: {"auth_token": "<uuid1>"}, to be sent as the `x-guest-id` header on later requests."""

        return {"auth_token": str(uuid1())}


lambda_handler = CreateGuest.lambda_handler()
