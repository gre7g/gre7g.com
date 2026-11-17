"""Test fetching an order"""

from http import HTTPStatus
import logging

from .base_test_classes import BaseTestCase

# Constants:
LOG = logging.getLogger(__name__)


class TestGetOrder(BaseTestCase):
    """Test fetching an order"""

    def test_no_id(self):
        """Should fail if there's no user ID"""
        response = self.get("/api/v1/order/order1_id")
        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_user(self) -> None:
        """Should fetch an order"""
        orders, order_dict = self.order_data()
        with self.create_records([(self.orders_table, orders[0]), (self.orders_table, orders[1])]):
            response = self.get(
                "/api/v1/order/order1_id",
                auth_user=self.regular_user,
            )
            assert response.status_code == HTTPStatus.OK
            assert response.json() == {"order": order_dict["orders"][0]}
