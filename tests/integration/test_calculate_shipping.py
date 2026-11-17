"""Test shipping calculation"""

from http import HTTPStatus
import logging

from .base_test_classes import BaseTestCase

# Constants:
LOG = logging.getLogger(__name__)


class TestCalculateShipping(BaseTestCase):
    """Test shipping calculation"""

    def test_logged_in(self) -> None:
        """Should inform the user that they're logged in"""
        cart, cart_dict = self.cart_data()
        with self.create_records([(self.carts_table, cart)]):
            response = self.post(
                "/api/v1/cart/shipping",
                auth_user=self.regular_user,
                json={},
            )
            assert response.status_code == HTTPStatus.CREATED
            assert response.json() == {"shipping_cost": 5.99, "user_status": "logged_in"}

    def test_may_log_in(self) -> None:
        """Should encourage the user to log in"""
        cart, cart_dict = self.guest_cart_no_downloads()
        with self.create_records([(self.carts_table, cart)]):
            response = self.post(
                "/api/v1/cart/shipping",
                guest_user="guest1_id",
                json={},
            )
            assert response.status_code == HTTPStatus.CREATED
            assert response.json() == {"shipping_cost": 5.99, "user_status": "may_log_in"}

    def test_must_log_in(self) -> None:
        """Should require the user to log in"""
        cart, cart_dict = self.guest_cart_data()
        with self.create_records([(self.carts_table, cart)]):
            response = self.post(
                "/api/v1/cart/shipping",
                guest_user="guest1_id",
                json={},
            )
            assert response.status_code == HTTPStatus.CREATED
            assert response.json() == {"shipping_cost": 5.99, "user_status": "must_log_in"}
