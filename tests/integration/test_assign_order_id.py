"""Test assigning an order ID"""

from http import HTTPStatus
import logging

from lib.local.integration_base import BaseTestCase

# Constants:
LOG = logging.getLogger(__name__)


class TestAssignOrderId(BaseTestCase):
    """Test assigning an order ID"""

    def test_happy_path(self) -> None:
        """Should assign an order ID"""
        response = self.post("/api/v1/cart", json={})
        assert response.status_code == HTTPStatus.CREATED
        result = response.json()
        assert len(result) == 1
        assert result["order_id"] and isinstance(result["order_id"], str)
