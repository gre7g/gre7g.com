"""
Log a click_id

POST /api/v1/click_id. Records an ad/referral click ID from the client in the audit log, along with whatever user and
guest identity accompanied the request. No authentication is required.

REQUIRES: AuditRW
"""

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext
import logging
import os
from typing import Any

from audit_log import AuditLogEvent
from lambda_base import LambdaBase

# Constants:
LOG = Logger(__name__) if os.getenv("AWS_LAMBDA_FUNCTION_NAME") else logging.getLogger(__name__)


class LogAudit(LambdaBase):
    """Log a click_id"""

    def handler(self, event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
        """Log a click_id

        Request body: {"click_id": "<id>"}
        Response: {}

        Raises KeyError (400) if click_id is missing."""
        click_id = self.body["click_id"]
        # The audit log write runs in a background thread; LambdaBase joins it before returning the response
        self.audit_log(AuditLogEvent.REGISTER_CLICK, click_id=click_id)

        return {}


lambda_handler = LogAudit.lambda_handler()
