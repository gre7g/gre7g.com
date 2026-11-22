"""Various utilities for audit logging

Audit events are written as individual JSON objects to the S3 bucket named by the "AUDIT_LOG_STORAGE" environment
variable, under "custom/YYYY-MM/<uuid>.json". Writes happen in a background thread so the lambda can keep working while
the S3 request is in flight.
"""

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
# Use the Powertools structured logger when running inside Lambda, plain stdlib logging otherwise (tests, local runs).
LOG = Logger(__name__) if os.getenv("AWS_LAMBDA_FUNCTION_NAME") else logging.getLogger(__name__)


class AuditLogEvent(StrEnum):
    """Audit log event types (the lowercase member name is stored as the "event" field)"""

    REGISTER_CLICK = auto()
    PLACE_ORDER = auto()
    CONFIRM_ORDER = auto()
    CART_MERGE = auto()


def audit_log(event: AuditLogEvent, **kwargs: Any) -> Thread:
    """Log an event to the audit log

    The S3 upload runs on a new, already-started thread. The caller is responsible for joining it before the Lambda
    invocation returns; otherwise the runtime may freeze the process and the write could be delayed or lost.
    "LambdaBase.audit_log" collects these threads and "LambdaBase.__call__" joins them.

    Args:
        event: The type of event being logged.
        **kwargs: Extra JSON-serializable fields to record. These are merged over the base record, so a "timestamp"
            or "event" keyword would override the generated values.

    Returns:
        The started thread performing the upload. Exceptions raised in the thread are not propagated to the caller.

    Raises:
        KeyError: If "AUDIT_LOG_STORAGE" is not set (raised synchronously, before the thread starts).
    """
    now = datetime.now(UTC)
    data = {"timestamp": now.isoformat(), "event": event.value}
    # The client, bucket, key, and body are all resolved here on the calling thread; only the network call itself
    # happens in the background.
    thread = Thread(
        target=boto3.client("s3").put_object,
        kwargs={
            "Bucket": os.environ["AUDIT_LOG_STORAGE"],
            # Partition by month for easy browsing/lifecycle rules; a UUID filename keeps concurrent writes from
            # colliding.
            "Key": f"custom/{now.strftime('%Y-%m')}/{str(uuid1())}.json",
            "Body": json.dumps(data | kwargs),
        },
    )
    thread.start()
    return thread
