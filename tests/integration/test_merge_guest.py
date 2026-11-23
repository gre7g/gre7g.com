"""
Test merging a guest cart into a user's cart

When a guest logs in, the client calls PUT /api/v1/guest with both the guest ID and the user's credentials so the
guest's cart is folded into the user's cart and the guest cart is deleted.
"""

from http import HTTPStatus
import logging

from .base_test_classes import BaseTestCase
from database import Cart, UserId

# Constants:
LOG = logging.getLogger(__name__)


class TestCartMerge(BaseTestCase):
    """Test merging a guest cart into a user's cart"""

    def test_missing_id(self):
        """Should fail when guest or user ID is missing"""
        # User ID only
        response = self.put(
            "/api/v1/guest",
            auth_user=self.regular_user,
            json={},
        )
        assert response.status_code == HTTPStatus.FORBIDDEN
        # Guest ID only
        response = self.put(
            "/api/v1/guest",
            guest_user=self.regular_user.user_id,
            json={},
        )
        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_bad_id(self):
        """Should fail when guest and user ID are identical"""
        # Merging a cart into itself would delete it, so the handler rejects this
        response = self.put(
            "/api/v1/guest",
            auth_user=self.regular_user,
            guest_user=self.regular_user.user_id,
            json={},
        )
        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_happy_path(self):
        """Should merge guest cart into a user account's"""
        # User cart holds PRODUCT1 (p1) and PRODUCT2 (p2); guest cart holds PRODUCT3 (p3) and PRODUCT4 (p2). PRODUCT4
        # should replace PRODUCT2 since they share a product ID, leaving three items.
        user_id = UserId(self.regular_user.user_id)  # noqa
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
            result = response.json()
            assert len(result) == 1
            result_cart_dict = result["products"]
            assert len(result_cart_dict) == 3
            assert guest_cart_dict["products"][0] in result_cart_dict
            assert guest_cart_dict["products"][1] in result_cart_dict
            assert user_cart_dict["products"][0] in result_cart_dict

            # Guest cart should be deleted
            result = self.carts_table.get_item(Key={"user_id": "guest1_id"})
            assert "Item" not in result

            # Guest items should be added, and user items should remain unless replaced by guest items
            result_cart = Cart.get(self.carts_table, user_id)
            assert len(result_cart.products) == 3
            assert guest_cart.products[0] in result_cart.products
            assert guest_cart.products[1] in result_cart.products
            assert user_cart.products[0] in result_cart.products
