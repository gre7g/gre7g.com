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
        """Should reject fetching an order without logging in"""
        response = self.get("/api/v1/order/order1_id")
        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_user(self) -> None:
        """Should fetch a single order with its download links signed"""
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

            # Should be signed now. The URL contents vary (the simulation returns a fixed fake URL, the cloud a real
            # presigned one), so just check that it looks like a URL and then fold it into the expected result.
            signed = result["order"]["products"][0]["downloads"]["test.zip"]
            assert signed.startswith("https://")
            order_dict["orders"][1]["products"][0]["downloads"]["test.zip"] = signed

            assert response.json() == {"order": order_dict["orders"][1]}
