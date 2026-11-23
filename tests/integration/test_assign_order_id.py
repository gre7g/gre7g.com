"""Test assigning an order ID"""

from http import HTTPStatus
import logging

from .base_test_classes import BaseTestCase

# Constants:
LOG = logging.getLogger(__name__)


class TestAssignOrderId(BaseTestCase):
    """Test assigning an order ID"""

    def test_happy_path(self) -> None:
        """Should assign an order ID"""
        # No authentication or guest ID is needed; the handler just hands back a fresh UUID
        response = self.post("/api/v1/cart", json={})
        assert response.status_code == HTTPStatus.CREATED
        result = response.json()
        # The response should contain only the order ID, and it should be a non-empty string
        assert len(result) == 1
        assert result["order_id"] and isinstance(result["order_id"], str)
