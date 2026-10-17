"""Test updating the shopping cart"""

from http import HTTPStatus
import logging

from gre7g_utils import Cart, UserId
from .base_test_classes import BaseTestCase

# Constants:
LOG = logging.getLogger(__name__)


class TestCartUpdate(BaseTestCase):
    """Test updating the shopping cart"""

    def test_no_id(self):
        """Should fail if there's no user ID and no guest ID"""
        cart, cart_dict = self.cart_data()
        response = self.put("/api/v1/cart", json=cart_dict)
        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_guest(self):
        """Should use the guest ID"""
        cart, cart_dict = self.cart_data()
        response = self.put(
            "/api/v1/cart",
            json=cart_dict,
            guest_user=self.regular_user.user_id,
        )
        assert response.status_code == HTTPStatus.OK
        user_id = UserId(self.regular_user.user_id)
        try:
            assert Cart.get(self.carts_table, user_id) == cart
        finally:
            self.carts_table.delete_item(Key={"user_id": user_id})

    def test_user(self) -> None:
        """Should use the user ID"""
        cart, cart_dict = self.cart_data()
        response = self.put(
            "/api/v1/cart",
            json=cart_dict,
            auth_user=self.regular_user,
            guest_user="some-guest-id",
        )
        assert response.status_code == HTTPStatus.OK
        user_id = UserId(self.regular_user.user_id)
        try:
            assert Cart.get(self.carts_table, user_id) == cart
        finally:
            self.carts_table.delete_item(Key={"user_id": user_id})
