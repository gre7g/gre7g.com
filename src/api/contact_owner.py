"""
Contact site owner

POST /api/v1/contact. Forwards a contact-form message to the site owner's mailbox. No authentication is required, but
any user/guest identity on the request is included in the e-mail to help the owner follow up.

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
        """Contact site owner

        Request body: {"name": str, "email": str, "message": str}
        Response: {}

        Raises KeyError (400) if a body field is missing, or a generic Exception (500) if the e-mail could not be sent.
        """
        # repr() so that a missing identity shows up as "None" in the e-mail rather than an empty string
        user = repr(self.user_id)
        guest = repr(self.guest_id)
        # The address the user typed may differ from the one on their Cognito account; include both
        official_email = repr(self.get_email_by_sub() if self.user_id else None)
        name = self.body["name"]
        email = self.body["email"]
        message = self.body["message"]
        success = send_email_home(
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
        if not success:
            raise Exception("Unable to contact site owner")

        return {}


lambda_handler = ContactOwner.lambda_handler()
