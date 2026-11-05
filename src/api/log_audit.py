"""
Log a click_id

REQUIRES: AuditRW
"""

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext
import logging
import os
from typing import Any

from gre7g_utils import LambdaBase, AuditLogEvent

# Constants:
LOG = Logger(__name__) if os.getenv("AWS_LAMBDA_FUNCTION_NAME") else logging.getLogger(__name__)


class LogAudit(LambdaBase):
    """Log a click_id"""

    def handler(self, event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
        """Log a click_id"""
        click_id = self.body["click_id"]
        self.audit_log(AuditLogEvent.REGISTER_CLICK, click_id=click_id)

        return {}


lambda_handler = LogAudit.lambda_handler()
