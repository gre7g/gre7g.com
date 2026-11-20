"""Test order confirmation"""

from copy import deepcopy
from decimal import Decimal
from freezegun import freeze_time
from http import HTTPStatus
import logging
from unittest.mock import patch, call, Mock

from .base_test_classes import BaseTestCase
import lambda_base
from lib.local.integration_base import NO_CLOUD
from src.api import confirm_order

# Constants:
LOG = logging.getLogger(__name__)


class TestConfirmOrder(BaseTestCase):
    """Test order confirmation"""

    @NO_CLOUD
    @patch("lambda_base.LambdaBase.get_paypal_controller")
    @patch("src.api.confirm_order.send_email_home")
    @patch("lambda_base.LambdaBase.audit_log")
    @patch("src.api.confirm_order.APIHelper")
    @freeze_time("2026-11-13T12:47:52.959734+00:00")
    def test_happy_path(self, api_helper, *_args) -> None:
        """Should confirm an order placed with PayPal"""
        # Track calls we care about
        mock = Mock()
        lambda_base.LambdaBase.audit_log = mock.audit_log
        confirm_order.send_email_home = mock.send_email_home
        lambda_base.LambdaBase.get_paypal_controller = mock.get_paypal_controller

        # PRODUCT3 has a digital download, so the signing process will modify the object in place. We don't want to mess
        # up other tests, so make a copy of it.
        product3 = deepcopy(self.PRODUCT3)

        # Inject test order
        api_helper.to_dictionary.return_value = {
            "status": "COMPLETED",
            "links": {},
            "payment_source": {},
            "purchase_units": [
                {
                    "payee": {},
                    "payments": {
                        "captures": [
                            {
                                "status": "COMPLETED",
                                "links": {},
                                "seller_protection": {},
                            }
                        ]
                    },
                    "items": [
                        {
                            "sku": product3.product_id,
                            "name": product3.name,
                            "quantity": "1",
                            "unit_amount": {"currency_code": "USD", "value": "15.99"},
                            "category": "DIGITAL_GOODS",
                        },
                        {
                            "sku": self.OUT_OF_STOCK4.product_id,
                            "name": self.OUT_OF_STOCK4.name,
                            "quantity": "1",
                            "unit_amount": {"currency_code": "USD", "value": "18.49"},
                            "category": "PHYSICAL_GOODS",
                        },
                    ],
                    "amount": {
                        "currency_code": "USD",
                        "breakdown": {
                            "item_total": {"currency_code": "USD", "value": "34.48"},
                            "shipping": {"currency_code": "USD", "value": "5.00"},
                        },
                        "value": "39.48",
                    },
                    "reference_id": "123-456",
                }
            ],
        }

        cart, cart_dict = self.digital_cart_data()
        with self.create_records(
            [(self.carts_table, cart), (self.products_table, product3), (self.products_table, self.OUT_OF_STOCK4)]
        ):
            response = self.put(
                "/api/v1/order/abc",
                auth_user=self.regular_user,
                json={},
            )
            assert response.status_code == HTTPStatus.OK

            try:
                assert response.json() == {
                    "order": {
                        "discount": 0.0,
                        "notes": ["11/13/2026 12:47: order placed"],
                        "order_id": "123-456",
                        "products": [
                            {
                                "child_ids": [],
                                "cost_per": 15.99,
                                "description": "cc",
                                "downloads": {"test.zip": "https://example.com/test.zip?auth_id=1234567890"},
                                "images": [],
                                "listing_path": "books/small-world",
                                "media": "audiobook",
                                "name": "Small World",
                                "parent_id": None,
                                "product_id": "p3",
                                "quantity": 1,
                                "short_desc": "--",
                                "status": "available",
                            },
                            {
                                "child_ids": [],
                                "cost_per": 18.49,
                                "description": "dd",
                                "downloads": {},
                                "images": [],
                                "listing_path": "books/long-way-home",
                                "media": "paperback",
                                "name": "Long Way Home",
                                "parent_id": None,
                                "product_id": "p2",
                                "quantity": 1,
                                "short_desc": "--",
                                "status": "available",
                            },
                        ],
                        "shipping_cost": 5.0,
                        "subtotal_cost": 34.48,
                        "timestamp": "2026-11-13T12:47:52.959734+00:00",
                        "total_cost": 39.48,
                        "transaction_id": "abc",
                    }
                }

                # Verify calls happened
                mock.assert_has_calls(
                    [
                        call.get_paypal_controller(),
                        call.get_paypal_controller().capture_order({"id": "abc", "prefer": "return=representation"}),
                        call.audit_log(
                            lambda_base.AuditLogEvent.CONFIRM_ORDER,
                            order={
                                "status": "COMPLETED",
                                "purchase_units": [
                                    {
                                        "payments": {"captures": [{"status": "COMPLETED"}]},
                                        "items": [
                                            {
                                                "sku": "p3",
                                                "name": "Small World",
                                                "quantity": "1",
                                                "unit_amount": {"currency_code": "USD", "value": "15.99"},
                                                "category": "DIGITAL_GOODS",
                                            },
                                            {
                                                "sku": "p2",
                                                "name": "Long Way Home",
                                                "quantity": "1",
                                                "unit_amount": {"currency_code": "USD", "value": "18.49"},
                                                "category": "PHYSICAL_GOODS",
                                            },
                                        ],
                                        "amount": {
                                            "currency_code": "USD",
                                            "breakdown": {
                                                "item_total": {"currency_code": "USD", "value": "34.48"},
                                                "shipping": {"currency_code": "USD", "value": "5.00"},
                                            },
                                            "value": "39.48",
                                        },
                                        "reference_id": "123-456",
                                    }
                                ],
                            },
                        ),
                        call.send_email_home(
                            "Inventory Error",
                            'Insufficient stock of "Long Way Home" to fulfill order 123-456',
                        ),
                    ]
                )

                # Verify that shopping cart got emptied
                result = self.carts_table.get_item(Key={"user_id": self.regular_user.user_id})
                assert "Item" not in result

                # Verify order was created
                result = self.orders_table.get_item(Key={"user_id": self.regular_user.user_id, "order_id": "123-456"})
                assert result["Item"] == {
                    "discount": Decimal("0.00"),
                    "notes": ["11/13/2026 12:47: order placed"],
                    "order_id": "123-456",
                    "products": [
                        {
                            "child_ids": [],
                            "cost_per": Decimal("15.99"),
                            "description": "cc",
                            "downloads": {"test.zip": "https://example.com/test.zip?auth_id=1234567890"},
                            "images": [],
                            "listing_path": "books/small-world",
                            "media": "audiobook",
                            "name": "Small World",
                            "parent_id": None,
                            "product_id": "p3",
                            "quantity": 1,
                            "short_desc": "--",
                            "status": "available",
                            "version": 1,
                        },
                        {
                            "child_ids": [],
                            "cost_per": Decimal("18.49"),
                            "description": "dd",
                            "downloads": {},
                            "images": [],
                            "listing_path": "books/long-way-home",
                            "media": "paperback",
                            "name": "Long Way Home",
                            "parent_id": None,
                            "product_id": "p2",
                            "quantity": 1,
                            "short_desc": "--",
                            "status": "available",
                            "version": 1,
                        },
                    ],
                    "shipping_cost": Decimal("5.00"),
                    "subtotal_cost": Decimal("34.48"),
                    "timestamp": "2026-11-13T12:47:52.959734+00:00",
                    "total_cost": Decimal("39.48"),
                    "transaction_id": "abc",
                    "user_id": "f65b7878-a973-11f1-874a-64d69adcd141",
                    "version": 1,
                }
            finally:
                # Clean up
                self.orders_table.delete_item(Key={"user_id": self.regular_user.user_id, "order_id": "123-456"})
