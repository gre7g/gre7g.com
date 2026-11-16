"""
Contact site owner

REQUIRES: Gmail, GetUser
"""

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext
import logging
import os
from typing import Any

from gmail import send_email_home
from lambda_base import LambdaBase

# Constants:
LOG = Logger(__name__) if os.getenv("AWS_LAMBDA_FUNCTION_NAME") else logging.getLogger(__name__)


class ContactOwner(LambdaBase):
    """Contact site owner"""

    def handler(self, event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
        """Contact site owner"""
        user = repr(self.user_id)
        guest = repr(self.guest_id)
        official_email = repr(self.get_email_by_sub())
        name = self.body["name"]
        email = self.body["email"]
        message = self.body["message"]
        send_email_home(
            "Contact from gre7g.com",
            f"""
User: {user}
Guest: {guest}
Official email: {official_email}

Name: {name}
Input e-mail: {email}
Message:
{message}""",
        )

        return {}
