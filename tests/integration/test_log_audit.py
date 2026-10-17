"""Test adding an audit event"""

from http import HTTPStatus
import logging

from .base_test_classes import BaseTestCase
from gre7g_utils import AuditLogEvent

# Constants:
LOG = logging.getLogger(__name__)


class TestLogAudit(BaseTestCase):
    """Test adding an audit event"""

    def test_happy_path(self) -> None:
        """Test adding an audit event"""
        response = self.post(
            "/api/v1/click_id",
            auth_user=self.regular_user,
            guest_user="some-guest-id",
            json={"click_id": "some click id"},
        )
        assert response.status_code == HTTPStatus.OK

        objects = self.get_all_audit_objects()
        try:
            needle = {
                "event": AuditLogEvent.REGISTER_CLICK.value,
                "user_id": self.regular_user.user_id,
                "guest_id": "some-guest-id",
                "click_id": "some click id",
            }
            assert self.obj_in_audit_objects(needle, objects)
        finally:
            self.delete_audit_objects(objects)
