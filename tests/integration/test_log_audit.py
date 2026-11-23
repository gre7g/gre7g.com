"""
Test adding an audit event

The audit log writes to S3 on a background thread. In the local simulation that thread is replaced with MockThread so
the write happens synchronously and can be checked immediately.
"""

from dataclasses import dataclass, field
from http import HTTPStatus
import logging
from typing import Callable, Any
from unittest.mock import patch

from .base_test_classes import BaseTestCase
from lib.local.integration_base import CLOUD_ONLY, NO_CLOUD
import audit_log

# Constants:
LOG = logging.getLogger(__name__)


@dataclass
class MockThread:
    """Stand-in for threading.Thread that runs the target synchronously when started"""

    target: Callable
    args: tuple = ()
    kwargs: dict[str, Any] = field(default_factory=dict)
    daemon: bool = False

    def start(self) -> None:
        """Start the thread"""
        self.target(*self.args, **self.kwargs)

    def join(self):
        """Thread is already done, so yeah"""
        pass


class TestLogAudit(BaseTestCase):
    """Test adding an audit event"""

    def add_audit_event(self):
        """Register a click ID and verify that a matching audit object was written to S3"""
        response = self.post(
            "/api/v1/click_id",
            auth_user=self.regular_user,
            guest_user="some-guest-id",
            json={"click_id": "some click id"},
        )
        assert response.status_code == HTTPStatus.CREATED

        # Match on the fields we sent (plus the caller's identity); remove the objects afterward so they don't leak into
        # other tests' searches
        objects = self.get_all_audit_objects()
        try:
            needle = {
                "event": audit_log.AuditLogEvent.REGISTER_CLICK.value,
                "user_id": self.regular_user.user_id,
                "guest_id": "some-guest-id",
                "click_id": "some click id",
            }
            assert self.obj_in_audit_objects(needle, objects)
        finally:
            self.delete_audit_objects(objects)

    # Test locally. Can't patch functions in the cloud.
    @NO_CLOUD
    @patch("audit_log.Thread")
    def test_simulation(self, *_args) -> None:
        """Should write a click ID audit event in the local simulation"""
        # The patch decorator restores audit_log.Thread after the test; replace the patched value with MockThread so
        # the audit write runs inline
        audit_log.Thread = MockThread
        self.add_audit_event()

    @CLOUD_ONLY
    def test_cloud(self) -> None:
        """Should write a click ID audit event in the cloud"""
        self.add_audit_event()
