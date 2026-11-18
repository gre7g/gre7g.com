"""Test contact form"""

from http import HTTPStatus
import logging
from unittest.mock import patch

from .base_test_classes import BaseTestCase
from lib.local.integration_base import NO_CLOUD

# Constants:
LOG = logging.getLogger(__name__)


class TestContactOwner(BaseTestCase):
    """Test contact form"""

    @NO_CLOUD
    @patch("src.api.contact_owner.send_email_home")
    def test_logged_out(self, send_email_home) -> None:
        response = self.post(
            "/api/v1/contact",
            guest_user="some-guest-id",
            json={"name": "Jim Jones", "email": "jim@jones.com", "message": "Howdy"},
        )
        assert response.status_code == HTTPStatus.CREATED
        assert response.json() == {}
        send_email_home.assert_called_once_with(
            "Contact from gre7g.com",
            """
User: None
Guest: 'some-guest-id'
Official email: None

Name: Jim Jones
Input e-mail: jim@jones.com
Message:
Howdy""",
        )

    @NO_CLOUD
    @patch("src.api.contact_owner.send_email_home")
    def test_logged_in(self, send_email_home) -> None:
        """Should send an e-mail to the site owner"""
        response = self.post(
            "/api/v1/contact",
            auth_user=self.regular_user,
            json={"name": "Jim Jones", "email": "jim@jones.com", "message": "Howdy"},
        )
        assert response.status_code == HTTPStatus.CREATED
        assert response.json() == {}
        send_email_home.assert_called_once_with(
            "Contact from gre7g.com",
            f"""
User: '{self.regular_user.user_id}'
Guest: None
Official email: 'address@example.com'

Name: Jim Jones
Input e-mail: jim@jones.com
Message:
Howdy""",
        )
