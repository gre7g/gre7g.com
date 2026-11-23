"""
Test shipping calculation

Besides the shipping cost, the handler tells the client whether the user needs to log in before checking out: guests may
buy physical items but must log in to buy digital downloads.
"""

from http import HTTPStatus
import logging

from .base_test_classes import BaseTestCase

# Constants:
LOG = logging.getLogger(__name__)


class TestCalculateShipping(BaseTestCase):
    """Test shipping calculation"""

    def test_logged_in(self) -> None:
        """Should report a logged-in status for an authenticated user"""
        # All-physical cart, so shipping applies
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
        """Should let a guest with only physical items check out without logging in"""
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
        """Should require a guest to log in when the cart contains a digital download"""
        # PRODUCT3 is an audiobook and PRODUCT4 is a paperback; the physical item still incurs shipping
        cart, cart_dict = self.guest_cart_data()
        with self.create_records([(self.carts_table, cart)]):
            response = self.post(
                "/api/v1/cart/shipping",
                guest_user="guest1_id",
                json={},
            )
            assert response.status_code == HTTPStatus.CREATED
            assert response.json() == {"shipping_cost": 5.99, "user_status": "must_log_in"}
