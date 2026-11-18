"""Test order confirmation"""

from freezegun import freeze_time
from http import HTTPStatus
import logging
from unittest.mock import patch, call

from .base_test_classes import BaseTestCase
from lambda_base import AuditLogEvent
from lib.local.integration_base import NO_CLOUD

# Constants:
LOG = logging.getLogger(__name__)


class TestConfirmOrder(BaseTestCase):
    """Test order confirmation"""

    @NO_CLOUD
    @patch("lambda_base.LambdaBase.get_paypal_controller")
    @patch("src.api.confirm_order.APIHelper")
    @patch("src.api.confirm_order.send_email_home")
    @patch("lambda_base.LambdaBase.audit_log")
    @freeze_time("2026-11-13T12:47:52.959734+00:00")
    def test_happy_path(self, audit_log, send_email_home, api_helper, get_paypal_controller) -> None:
        """Should confirm an order placed with PayPal"""
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
                            "sku": self.PRODUCT3.product_id,
                            "name": self.PRODUCT3.name,
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
            [(self.carts_table, cart), (self.products_table, self.PRODUCT3), (self.products_table, self.OUT_OF_STOCK4)]
        ):
            response = self.put(
                "/api/v1/order/abc",
                auth_user=self.regular_user,
                json={},
            )
            assert response.status_code == HTTPStatus.OK
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
                }
            }
            audit_log.assert_called_once_with(
                AuditLogEvent.CONFIRM_ORDER,
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
            )
            send_email_home.assert_called_once_with(
                "Inventory Error",
                'Insufficient stock of "Long Way Home" to fulfill order 123-456',
            )
            get_paypal_controller.assert_has_calls(
                [call(), call().capture_order({"id": "abc", "prefer": "return=representation"})]
            )
