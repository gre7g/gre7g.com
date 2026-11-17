"""Test order submission"""

from dataclasses import dataclass, field
from http import HTTPStatus
import logging
from unittest.mock import patch, Mock

from .base_test_classes import BaseTestCase
from lib.local.integration_base import NO_CLOUD
import lambda_base
from src.api import place_order

# Constants:
LOG = logging.getLogger(__name__)
CREATED_ORDER = {
    "id": "1234",
    "links": [{"href": "url", "method": "GET", "rel": "verify"}],
    "status": "processing",
}

EXPECTED_PHYSICAL_RESPONSE = {
    "name": "OrderRequest",
    "args": [
        "CAPTURE",
        [
            {
                "args": [
                    {
                        "args": [
                            "USD",
                            "38.47",
                            {
                                "args": [
                                    {"args": ["USD", "32.48"], "kwargs": {}, "name": "Money"},
                                    {"args": ["USD", "5.99"], "kwargs": {}, "name": "Money"},
                                ],
                                "kwargs": {},
                                "name": "AmountBreakdown",
                            },
                        ],
                        "kwargs": {},
                        "name": "AmountWithBreakdown",
                    },
                    "123-456",
                ],
                "kwargs": {
                    "items": [
                        {
                            "args": [],
                            "kwargs": {
                                "category": "PHYSICAL_GOODS",
                                "description": "--",
                                "name": "Skeleton Crew",
                                "quantity": "1",
                                "sku": "p1",
                                "unit_amount": {
                                    "args": ["USD", "13.99"],
                                    "kwargs": {},
                                    "name": "Money",
                                },
                            },
                            "name": "Item",
                        },
                        {
                            "args": [],
                            "kwargs": {
                                "category": "PHYSICAL_GOODS",
                                "description": "--",
                                "name": "Long Way Home",
                                "quantity": "1",
                                "sku": "p2",
                                "unit_amount": {
                                    "args": ["USD", "18.49"],
                                    "kwargs": {},
                                    "name": "Money",
                                },
                            },
                            "name": "Item",
                        },
                    ]
                },
                "name": "PurchaseUnitRequest",
            }
        ],
    ],
    "kwargs": {},
}


@dataclass
class MockObject:
    name: str
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)

    def __call__(self, *args, **kwargs):
        return {"name": self.name, "args": args, "kwargs": kwargs}


class MockSdkClient(MockObject):
    def __call__(self, *args, **kwargs):
        obj = MockSdkClient("MockSdkClient", args, kwargs)
        obj.orders = self
        return obj

    def create_order(self, params):
        return Mock(body=CREATED_ORDER)


class TestPlaceOrder(BaseTestCase):
    """Test order submission"""

    @NO_CLOUD
    @patch("lambda_base.PaypalServersdkClient")
    def test_logged_out_download(self, paypal_serversdk_client) -> None:
        """Should not be able to order digital downloads when logged out"""
        cart, cart_dict = self.guest_cart_data()
        with self.create_records([(self.carts_table, cart)]):
            response = self.post(
                "/api/v1/order",
                guest_user="guest1_id",
                json={},
            )
            assert response.status_code == HTTPStatus.UNAUTHORIZED

    @NO_CLOUD
    @patch("src.api.place_order.APIHelper", to_dictionary=lambda x: x)
    @patch("src.api.place_order.AmountBreakdown")
    @patch("src.api.place_order.AmountWithBreakdown")
    @patch("src.api.place_order.Item")
    @patch("src.api.place_order.Money")
    @patch("src.api.place_order.OrderRequest")
    @patch("src.api.place_order.PurchaseUnitRequest")
    @patch("lambda_base.ClientCredentialsAuthCredentials")
    @patch("lambda_base.Environment")
    @patch("lambda_base.LoggingConfiguration")
    @patch("lambda_base.RequestLoggingConfiguration")
    @patch("lambda_base.ResponseLoggingConfiguration")
    @patch("src.api.place_order.uuid1", return_value="123-456")
    @patch("lambda_base.PaypalServersdkClient")
    @patch("src.api.place_order.send_email_home")
    def test_stock_problem(self, send_email_home, *_args) -> None:
        """Should email us when a stock issue occurs"""
        place_order.AmountBreakdown = MockObject("AmountBreakdown")
        place_order.AmountWithBreakdown = MockObject("AmountWithBreakdown")
        place_order.Item = MockObject("Item")
        place_order.Money = MockObject("Money")
        place_order.OrderRequest = MockObject("OrderRequest")
        place_order.PurchaseUnitRequest = MockObject("PurchaseUnitRequest")
        lambda_base.ClientCredentialsAuthCredentials = MockObject("ClientCredentialsAuthCredentials")
        lambda_base.Environment = Mock(SANDBOX="SANDBOX", PRODUCTION="PRODUCTION")
        lambda_base.LoggingConfiguration = MockObject("LoggingConfiguration")
        lambda_base.RequestLoggingConfiguration = MockObject("RequestLoggingConfiguration")
        lambda_base.ResponseLoggingConfiguration = MockObject("ResponseLoggingConfiguration")
        lambda_base.PaypalServersdkClient = MockSdkClient("MockSdkClient")
        cart, cart_dict = self.cart_data()
        with self.create_records(
            [(self.carts_table, cart), (self.products_table, self.OUT_OF_STOCK), (self.products_table, self.PRODUCT2)]
        ):
            response = self.post(
                "/api/v1/order",
                auth_user=self.regular_user,
                json={},
            )
            assert response.status_code == HTTPStatus.CREATED
            assert response.json() == CREATED_ORDER

        send_email_home.assert_called_once_with("Cannot fulfill purchase warning", "Items: p1")

        # Check audit log too
        objects = self.get_all_audit_objects()
        try:
            needle = {
                "event": "place_order",
                "user_id": self.regular_user.user_id,
                "guest_id": None,
                "order_request": EXPECTED_PHYSICAL_RESPONSE,
            }
            assert self.obj_in_audit_objects(needle, objects)
        finally:
            self.delete_audit_objects(objects)

    @NO_CLOUD
    @patch("src.api.place_order.APIHelper", to_dictionary=lambda x: x)
    @patch("src.api.place_order.AmountBreakdown")
    @patch("src.api.place_order.AmountWithBreakdown")
    @patch("src.api.place_order.Item")
    @patch("src.api.place_order.Money")
    @patch("src.api.place_order.OrderRequest")
    @patch("src.api.place_order.PurchaseUnitRequest")
    @patch("lambda_base.ClientCredentialsAuthCredentials")
    @patch("lambda_base.Environment")
    @patch("lambda_base.LoggingConfiguration")
    @patch("lambda_base.RequestLoggingConfiguration")
    @patch("lambda_base.ResponseLoggingConfiguration")
    @patch("src.api.place_order.uuid1", return_value="123-456")
    @patch("lambda_base.PaypalServersdkClient")
    def test_logged_out_physical(self, *_args) -> None:
        """Should be able to order physical items when logged out"""
        place_order.AmountBreakdown = MockObject("AmountBreakdown")
        place_order.AmountWithBreakdown = MockObject("AmountWithBreakdown")
        place_order.Item = MockObject("Item")
        place_order.Money = MockObject("Money")
        place_order.OrderRequest = MockObject("OrderRequest")
        place_order.PurchaseUnitRequest = MockObject("PurchaseUnitRequest")
        lambda_base.ClientCredentialsAuthCredentials = MockObject("ClientCredentialsAuthCredentials")
        lambda_base.Environment = Mock(SANDBOX="SANDBOX", PRODUCTION="PRODUCTION")
        lambda_base.LoggingConfiguration = MockObject("LoggingConfiguration")
        lambda_base.RequestLoggingConfiguration = MockObject("RequestLoggingConfiguration")
        lambda_base.ResponseLoggingConfiguration = MockObject("ResponseLoggingConfiguration")
        lambda_base.PaypalServersdkClient = MockSdkClient("MockSdkClient")
        cart, cart_dict = self.cart_data()
        with self.create_records(
            [(self.carts_table, cart), (self.products_table, self.PRODUCT1), (self.products_table, self.PRODUCT2)]
        ):
            response = self.post(
                "/api/v1/order",
                auth_user=self.regular_user,
                json={},
            )
            assert response.status_code == HTTPStatus.CREATED
            assert response.json() == CREATED_ORDER

        # Check audit log too
        objects = self.get_all_audit_objects()
        try:
            needle = {
                "event": "place_order",
                "user_id": self.regular_user.user_id,
                "guest_id": None,
                "order_request": EXPECTED_PHYSICAL_RESPONSE,
            }
            assert self.obj_in_audit_objects(needle, objects)
        finally:
            self.delete_audit_objects(objects)

    @NO_CLOUD
    @patch("src.api.place_order.APIHelper", to_dictionary=lambda x: x)
    @patch("src.api.place_order.AmountBreakdown")
    @patch("src.api.place_order.AmountWithBreakdown")
    @patch("src.api.place_order.Item")
    @patch("src.api.place_order.Money")
    @patch("src.api.place_order.OrderRequest")
    @patch("src.api.place_order.PurchaseUnitRequest")
    @patch("lambda_base.ClientCredentialsAuthCredentials")
    @patch("lambda_base.Environment")
    @patch("lambda_base.LoggingConfiguration")
    @patch("lambda_base.RequestLoggingConfiguration")
    @patch("lambda_base.ResponseLoggingConfiguration")
    @patch("src.api.place_order.uuid1", return_value="123-456")
    @patch("lambda_base.PaypalServersdkClient")
    def test_logged_in(self, *_args) -> None:
        """Should be able to order digital items when logged in"""
        place_order.AmountBreakdown = MockObject("AmountBreakdown")
        place_order.AmountWithBreakdown = MockObject("AmountWithBreakdown")
        place_order.Item = MockObject("Item")
        place_order.Money = MockObject("Money")
        place_order.OrderRequest = MockObject("OrderRequest")
        place_order.PurchaseUnitRequest = MockObject("PurchaseUnitRequest")
        lambda_base.ClientCredentialsAuthCredentials = MockObject("ClientCredentialsAuthCredentials")
        lambda_base.Environment = Mock(SANDBOX="SANDBOX", PRODUCTION="PRODUCTION")
        lambda_base.LoggingConfiguration = MockObject("LoggingConfiguration")
        lambda_base.RequestLoggingConfiguration = MockObject("RequestLoggingConfiguration")
        lambda_base.ResponseLoggingConfiguration = MockObject("ResponseLoggingConfiguration")
        lambda_base.PaypalServersdkClient = MockSdkClient("MockSdkClient")
        cart, cart_dict = self.digital_cart_data()
        with self.create_records(
            [(self.carts_table, cart), (self.products_table, self.PRODUCT3), (self.products_table, self.PRODUCT4)]
        ):
            response = self.post(
                "/api/v1/order",
                auth_user=self.regular_user,
                json={},
            )
            assert response.status_code == HTTPStatus.CREATED
            assert response.json() == CREATED_ORDER

        # Check audit log too
        objects = self.get_all_audit_objects()
        try:
            needle = {
                "event": "place_order",
                "user_id": self.regular_user.user_id,
                "guest_id": None,
                "order_request": {
                    "args": [
                        "CAPTURE",
                        [
                            {
                                "args": [
                                    {
                                        "args": [
                                            "USD",
                                            "58.96",
                                            {
                                                "args": [
                                                    {"args": ["USD", "52.97"], "kwargs": {}, "name": "Money"},
                                                    {"args": ["USD", "5.99"], "kwargs": {}, "name": "Money"},
                                                ],
                                                "kwargs": {},
                                                "name": "AmountBreakdown",
                                            },
                                        ],
                                        "kwargs": {},
                                        "name": "AmountWithBreakdown",
                                    },
                                    "123-456",
                                ],
                                "kwargs": {
                                    "items": [
                                        {
                                            "args": [],
                                            "kwargs": {
                                                "category": "DIGITAL_GOODS",
                                                "description": "--",
                                                "name": "Small World",
                                                "quantity": "1",
                                                "sku": "p3",
                                                "unit_amount": {
                                                    "args": ["USD", "15.99"],
                                                    "kwargs": {},
                                                    "name": "Money",
                                                },
                                            },
                                            "name": "Item",
                                        },
                                        {
                                            "args": [],
                                            "kwargs": {
                                                "category": "PHYSICAL_GOODS",
                                                "description": "--",
                                                "name": "Long Way Home",
                                                "quantity": "2",
                                                "sku": "p2",
                                                "unit_amount": {
                                                    "args": ["USD", "18.49"],
                                                    "kwargs": {},
                                                    "name": "Money",
                                                },
                                            },
                                            "name": "Item",
                                        },
                                    ]
                                },
                                "name": "PurchaseUnitRequest",
                            }
                        ],
                    ],
                    "kwargs": {},
                    "name": "OrderRequest",
                },
            }
            assert self.obj_in_audit_objects(needle, objects)
        finally:
            self.delete_audit_objects(objects)
