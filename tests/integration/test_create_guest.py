"""Test creating a guest authorization"""

from http import HTTPStatus
import logging

from .base_test_classes import BaseTestCase

# Constants:
LOG = logging.getLogger(__name__)


class TestCreateGuest(BaseTestCase):
    """Test creating a guest authorization"""

    def test_happy_path(self) -> None:
        """Should create a guest authorization"""
        # Anyone may request a guest token, so no auth_user or guest_user is supplied
        response = self.post("/api/v1/guest", json={})
        assert response.status_code == HTTPStatus.CREATED
        result = response.json()
        # The response should contain only the token, and it should be a non-empty string
        assert len(result) == 1
        assert result["auth_token"] and isinstance(result["auth_token"], str)
