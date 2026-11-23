"""Test updating the shopping cart"""

from http import HTTPStatus
import logging

from database import Cart, UserId
from .base_test_classes import BaseTestCase

# Constants:
LOG = logging.getLogger(__name__)


class TestCartUpdate(BaseTestCase):
    """Test updating the shopping cart"""

    def test_no_id(self):
        """Should reject a cart update with neither a user ID nor a guest ID"""
        cart, cart_dict = self.cart_data()
        response = self.put("/api/v1/cart", json=cart_dict)
        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_guest(self):
        """Should save the cart under the guest ID when not logged in"""
        cart, cart_dict = self.guest_cart_data()
        response = self.put(
            "/api/v1/cart",
            json=cart_dict,
            guest_user="guest1_id",
        )
        assert response.status_code == HTTPStatus.OK
        try:
            assert Cart.get(self.carts_table, UserId("guest1_id")) == cart
        finally:
            self.carts_table.delete_item(Key={"user_id": "guest1_id"})

    def test_user(self) -> None:
        """Should save the cart under the user ID when both user and guest IDs are given"""
        cart, cart_dict = self.cart_data()
        response = self.put(
            "/api/v1/cart",
            json=cart_dict,
            auth_user=self.regular_user,
            guest_user="some-guest-id",
        )
        assert response.status_code == HTTPStatus.OK
        # The cart should be stored under the authenticated user, not "some-guest-id"; clean it up ourselves afterward
        user_id = UserId(self.regular_user.user_id)  # noqa
        try:
            assert Cart.get(self.carts_table, user_id) == cart
        finally:
            self.carts_table.delete_item(Key={"user_id": user_id})
