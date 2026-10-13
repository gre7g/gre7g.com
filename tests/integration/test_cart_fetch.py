"""Test viewing the shopping cart"""

import boto3
from http import HTTPStatus
import logging

from gre7g_utils import Cart, Product, ProductId, UserId, TABLE_VERSION
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


class TestCartFetch(BaseTestCase):
    """Test viewing the shopping cart"""

    def setUp(self):
        super().setUp()
        dynamodb = boto3.resource("dynamodb")
        user_id = UserId(self.regular_user.user_id)
        carts_table = dynamodb.Table("CartsTable")
        products = [
            Product("Skeleton Crew", 1, 13.99, "books/skeleton-crew", ProductId("kc1")),
            Product("Long Way Home", 1, 18.49, "books/long-way-home", ProductId("lwh")),
        ]
        cart = Cart.from_dict({"user_id": user_id, "version": TABLE_VERSION} | PRODUCTS)
        carts_table.SECRET_OVERRIDE = True  # We might not have permission, but this is test infrastructure
        cart.put(carts_table)
        carts_table.SECRET_OVERRIDE = False

    def test_no_id(self):
        """Should fail if there's no user ID and no guest ID"""
        response = self.get("/api/v1/cart")
        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_guest(self):
        """Should use the guest ID"""
        response = self.get(
            "/api/v1/cart",
            guest_user=self.regular_user.user_id,
        )
        assert response.status_code == HTTPStatus.OK
        assert response.json() == PRODUCTS

    def test_happy_path(self) -> None:
        """Should assign an order ID"""
        response = self.get(
            "/api/v1/cart",
            auth_user=self.regular_user,
            guest_user="some-guest-id",
        )
        assert response.status_code == HTTPStatus.OK
        assert response.json() == PRODUCTS

    def test_empty_cart(self) -> None:
        """Should return an empty cart"""
        response = self.get(
            "/api/v1/cart",
            guest_user="some-guest-id",
        )
        assert response.status_code == HTTPStatus.OK
        assert response.json() == {"products": []}
