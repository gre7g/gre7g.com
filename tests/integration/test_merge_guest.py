"""Should merge guest cart into a user account's"""

from http import HTTPStatus
import logging

from .base_test_classes import BaseTestCase
from gre7g_utils import Cart, UserId

# Constants:
LOG = logging.getLogger(__name__)


class TestCartMerge(BaseTestCase):
    """Should merge guest cart into a user account's"""

    def test_missing_id(self):
        """Should fail when guest or user ID is missing"""
        response = self.put(
            "/api/v1/guest",
            auth_user=self.regular_user,
            json={},
        )
        assert response.status_code == HTTPStatus.BAD_REQUEST
        response = self.put(
            "/api/v1/guest",
            guest_user=self.regular_user.user_id,
            json={},
        )
        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_bad_id(self):
        """Should fail when guest and user ID are identical"""
        response = self.put(
            "/api/v1/guest",
            auth_user=self.regular_user,
            guest_user=self.regular_user.user_id,
            json={},
        )
        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_happy_path(self):
        """Should merge guest cart into a user account's"""
        user_id = UserId(self.regular_user.user_id)
        user_cart, user_cart_dict = self.cart_data()
        guest_cart, guest_cart_dict = self.guest_cart_data()
        with self.create_records([(self.carts_table, user_cart), (self.carts_table, guest_cart)]):
            response = self.put(
                "/api/v1/guest",
                auth_user=self.regular_user,
                guest_user="guest1_id",
                json={},
            )
            assert response.status_code == HTTPStatus.OK

            # Guest cart should be deleted
            result = self.carts_table.get_item(Key={"user_id": "guest1_id"})
            assert "Item" not in result

            # Guest items should be added, and user items should remain unless replaced by guest items
            result_cart = Cart.get(self.carts_table, user_id)
            assert len(result_cart.products) == 3
            assert guest_cart.products[0] in result_cart.products
            assert guest_cart.products[1] in result_cart.products
            assert user_cart.products[0] in result_cart.products
