"""Should return all the products"""

from http import HTTPStatus
import logging

from .base_test_classes import BaseTestCase

# Constants:
LOG = logging.getLogger(__name__)


class TestCartFetch(BaseTestCase):
    """Should return all the products"""

    def test_happy_path(self):
        """Should return all the products"""
        products, product_dict = self.cart_data()
        with self.create_records([(self.products_table, product) for product in products.products]):
            response = self.get("/api/v1/products")
            assert response.status_code == HTTPStatus.OK
            result = response.json()
            assert len(result) == 1
            assert len(result["products"]) >= len(product_dict["products"])
            assert all(product in result["products"] for product in product_dict["products"])
