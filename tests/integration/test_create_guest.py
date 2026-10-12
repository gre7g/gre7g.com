"""Test creating a guest authorization"""

from http import HTTPStatus
import logging

from integration_base import BaseTestCase

# Constants:
LOG = logging.getLogger(__name__)


class TestCreateGuest(BaseTestCase):
    """Test creating a guest authorization"""

    def test_happy_path(self) -> None:
        """Should create a guest authorization"""
        response = self.post("/api/v1/guest", json={})
        assert response.status_code == HTTPStatus.OK
        result = response.json()
        assert len(result) == 1
        assert result["auth_token"] and isinstance(result["auth_token"], str)
