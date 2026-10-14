"""Test updating the shopping cart"""

from http import HTTPStatus
import logging

from gre7g_utils import Cart, UserId, Product, ProductId
from integration_base import BaseTestCase

# Constants:
LOG = logging.getLogger(__name__)
PRODUCTS = {
    "products": [
        {
            "name": "Skeleton Crew",
            "quantity": 1,
            "cost_per": 13.99,
            "listing_path": "books/skeleton-crew",
            "product_id": "kc1",
        },
        {
            "name": "Long Way Home",
            "quantity": 1,
            "cost_per": 18.49,
            "listing_path": "books/long-way-home",
            "product_id": "lwh",
        },
    ]
}


class TestCartUpdate(BaseTestCase):
    """Test updating the shopping cart"""

    def test_no_id(self):
        """Should fail if there's no user ID and no guest ID"""
        response = self.put("/api/v1/cart", json=PRODUCTS)
        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_guest(self):
        """Should use the guest ID"""
        response = self.put(
            "/api/v1/cart",
            json=PRODUCTS,
            guest_user=self.regular_user.user_id,
        )
        assert response.status_code == HTTPStatus.OK
        user_id = UserId(self.regular_user.user_id)
        cart = Cart.get(self.carts_table, user_id)
        self.carts_table.delete_item(Key={"user_id": user_id})
        assert cart == Cart(
            user_id,
            [
                Product("Skeleton Crew", 1, 13.99, "books/skeleton-crew", ProductId("kc1")),
                Product("Long Way Home", 1, 18.49, "books/long-way-home", ProductId("lwh")),
            ],
        )

    def test_user(self) -> None:
        """Should use the user ID"""
        response = self.put(
            "/api/v1/cart",
            json=PRODUCTS,
            auth_user=self.regular_user,
            guest_user="some-guest-id",
        )
        assert response.status_code == HTTPStatus.OK
        user_id = UserId(self.regular_user.user_id)
        cart = Cart.get(self.carts_table, user_id)
        self.carts_table.delete_item(Key={"user_id": user_id})
        assert cart == Cart(
            user_id,
            [
                Product("Skeleton Crew", 1, 13.99, "books/skeleton-crew", ProductId("kc1")),
                Product("Long Way Home", 1, 18.49, "books/long-way-home", ProductId("lwh")),
            ],
        )
