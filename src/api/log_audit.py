"""Log a click_id"""

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext
import json
import logging
import os
from typing import Any

from gre7g_utils import LambdaBase, AuditLog

# Constants:
LOG = Logger(__name__) if os.getenv("AWS_LAMBDA_FUNCTION_NAME") else logging.getLogger(__name__)


class LogAudit(LambdaBase):
    """Log a click_id"""

    def handler(self, event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
        """Log a click_id"""
        assert self.audit_log_table

        body = json.loads(event["body"])
        click_id = body["click_id"]

        AuditLog({"user_id": self.user_id, "guest_id": self.guest_id, "click_id": click_id}).put(self.audit_log_table)

        return {}


lambda_handler = LogAudit.lambda_handler()
