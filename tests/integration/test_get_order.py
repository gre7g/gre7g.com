"""Test fetching an order"""

from copy import deepcopy
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

        # PRODUCT3 has a digital download, so the signing process will modify the object in place. We don't want to mess
        # up other tests, so make a copy of it.
        product3 = deepcopy(self.PRODUCT3)
        orders[1].products[0] = product3
        p_dict3 = deepcopy(self.P_DICT3)
        order_dict["orders"][1]["products"][0] = p_dict3

        # Shouldn't be signed yet
        assert product3.downloads["test.zip"] is None

        with self.create_records([(self.orders_table, orders[1])]):
            response = self.get(
                "/api/v1/order/order2_id",
                auth_user=self.regular_user,
            )
            assert response.status_code == HTTPStatus.OK
            result = response.json()

            # Should be signed now
            expect = "https://example.com/test.zip?auth_id=1234567890"
            assert result["order"]["products"][0]["downloads"]["test.zip"] == expect
            order_dict["orders"][1]["products"][0]["downloads"]["test.zip"] = expect

            assert response.json() == {"order": order_dict["orders"][1]}
