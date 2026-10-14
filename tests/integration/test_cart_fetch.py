"""Test viewing the shopping cart"""

from http import HTTPStatus
import logging

from .base_test_classes import BaseTestCase

# Constants:
LOG = logging.getLogger(__name__)


class TestCartFetch(BaseTestCase):
    """Test viewing the shopping cart"""

    def test_no_id(self):
        """Should fail if there's no user ID and no guest ID"""
        response = self.get("/api/v1/cart")
        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_guest(self):
        """Should use the guest ID"""
        cart, cart_dict = self.cart_data()
        with self.create_records([(self.carts_table, cart)]):
            response = self.get(
                "/api/v1/cart",
                guest_user=self.regular_user.user_id,
            )
            assert response.status_code == HTTPStatus.OK
            assert response.json() == cart_dict

    def test_user(self) -> None:
        """Should use the user ID"""
        cart, cart_dict = self.cart_data()
        with self.create_records([(self.carts_table, cart)]):
            response = self.get(
                "/api/v1/cart",
                auth_user=self.regular_user,
                guest_user="some-guest-id",
            )
            assert response.status_code == HTTPStatus.OK
            assert response.json() == cart_dict

    def test_empty_cart(self) -> None:
        """Should return an empty cart"""
        response = self.get(
            "/api/v1/cart",
            guest_user="some-guest-id",
        )
        assert response.status_code == HTTPStatus.OK
        assert response.json() == {"products": []}
