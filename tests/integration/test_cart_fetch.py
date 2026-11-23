"""Test viewing the shopping cart"""

from http import HTTPStatus
import logging

from .base_test_classes import BaseTestCase

# Constants:
LOG = logging.getLogger(__name__)


class TestCartFetch(BaseTestCase):
    """Test viewing the shopping cart"""

    def test_no_id(self):
        """Should reject a request with neither a user ID nor a guest ID"""
        response = self.get("/api/v1/cart")
        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_guest(self):
        """Should look up the cart by guest ID when not logged in"""
        # Carts are keyed by a single ID, so storing the cart under the regular user's ID and passing that same value
        # as the guest ID proves the guest header is used for the lookup
        cart, cart_dict = self.cart_data()
        with self.create_records([(self.carts_table, cart)]):
            response = self.get(
                "/api/v1/cart",
                guest_user=self.regular_user.user_id,
            )
            assert response.status_code == HTTPStatus.OK
            assert response.json() == cart_dict

    def test_user(self) -> None:
        """Should prefer the user ID over the guest ID when both are given"""
        # The cart is stored under the user ID; the guest ID has no cart, so getting the cart back means the user ID won
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
        """Should return an empty cart when none has been saved"""
        response = self.get(
            "/api/v1/cart",
            guest_user="some-guest-id",
        )
        assert response.status_code == HTTPStatus.OK
        assert response.json() == {"products": []}
