"""Test viewing the shopping cart"""

from http import HTTPStatus
import logging

from .base_test_classes import BaseTestCase

# Constants:
LOG = logging.getLogger(__name__)


class TestGetOrders(BaseTestCase):
    def test_no_id(self):
        """Should fail if there's no user ID"""
        response = self.get("/api/v1/order")
        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_user(self) -> None:
        """Should fetch all orders"""
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
            assert len(orders) == 2
            assert order_dict["orders"][0] in orders
            assert order_dict["orders"][1] in orders
