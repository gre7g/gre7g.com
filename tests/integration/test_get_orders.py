"""Test fetching order history"""

from http import HTTPStatus
import logging

from .base_test_classes import BaseTestCase

# Constants:
LOG = logging.getLogger(__name__)


class TestGetOrders(BaseTestCase):
    """Test fetching order history"""

    def test_no_id(self):
        """Should reject fetching order history without logging in"""
        response = self.get("/api/v1/order")
        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_user(self) -> None:
        """Should fetch all of the user's orders"""
        orders, order_dict = self.order_data()
        with self.create_records([(self.orders_table, orders[0]), (self.orders_table, orders[1])]):
            response = self.get(
                "/api/v1/order",
                auth_user=self.regular_user,
            )
            assert response.status_code == HTTPStatus.OK
            result = response.json()
            assert len(result) == 1
            orders = result["orders"]
            # Order of results isn't guaranteed, so check membership rather than comparing lists
            assert len(orders) == 2
            assert order_dict["orders"][0] in orders
            assert order_dict["orders"][1] in orders
