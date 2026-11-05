"""Various utilities for audit logging"""

from aws_lambda_powertools import Logger
import boto3
from datetime import datetime, UTC
from enum import auto, StrEnum
import json
import logging
import os
from threading import Thread
from typing import Any
from uuid import uuid1

# Constants:
LOG = Logger(__name__) if os.getenv("AWS_LAMBDA_FUNCTION_NAME") else logging.getLogger(__name__)


class AuditLogEvent(StrEnum):
    """Audit log event types"""

    REGISTER_CLICK = auto()
    PLACE_ORDER = auto()
    CONFIRM_ORDER = auto()
    CART_MERGE = auto()


def audit_log(event: AuditLogEvent, **kwargs: Any) -> Thread:
    """Log an event to the audit log"""
    now = datetime.now(UTC)
    data = {"timestamp": now.isoformat(), "event": event.value}
    thread = Thread(
        target=boto3.client("s3").put_object,
        kwargs={
            "Bucket": os.environ["AUDIT_LOG_STORAGE"],
            "Key": f"custom/{now.strftime('%Y-%m')}/{str(uuid1())}.json",
            "Body": json.dumps(data | kwargs),
        },
    )
    thread.start()
    return thread
