"""Test adding an audit event"""

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
    """Mock thread"""

    target: Callable
    args: tuple = ()
    kwargs: dict[str, Any] = field(default_factory=dict)
    daemon: bool = False

    def start(self) -> None:
        """Start the thread"""
        self.target(*self.args, **self.kwargs)


class TestLogAudit(BaseTestCase):
    """Test adding an audit event"""

    def add_audit_event(self):
        response = self.post(
            "/api/v1/click_id",
            auth_user=self.regular_user,
            guest_user="some-guest-id",
            json={"click_id": "some click id"},
        )
        assert response.status_code == HTTPStatus.CREATED

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

    @NO_CLOUD
    @patch("audit_log.Thread")
    def test_simulation(self, *_args) -> None:
        """Test adding an audit event in simulation"""
        audit_log.Thread = MockThread
        self.add_audit_event()

    @CLOUD_ONLY
    def test_cloud(self) -> None:
        """Test adding an audit event in the cloud"""
        self.add_audit_event()
