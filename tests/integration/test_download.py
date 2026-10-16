"""Should produce an URL for downloading the file"""

from http import HTTPStatus
import logging

from .base_test_classes import BaseTestCase

# Constants:
LOG = logging.getLogger(__name__)


class TestDownload(BaseTestCase):
    """Should produce an URL for downloading the file"""

    def test_missing_id(self):
        """Should fail when user ID is missing"""
        response = self.get(
            "/api/v1/download/order2_id",
        )
        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_happy_path(self) -> None:
        """Should produce an URL for downloading the file"""
        orders, order_dict = self.order_data()
        with self.create_records([(self.orders_table, orders[0]), (self.orders_table, orders[1])]):
            response = self.get(
                "/api/v1/download/order2_id",
                auth_user=self.regular_user,
            )
            assert response.status_code == HTTPStatus.OK
            result = response.json()
            assert len(result) == 1
            assert len(result["files"]) == 1
            url = result["files"]["test.zip"]
            assert "test.zip" != url
            assert "test.zip" in url
