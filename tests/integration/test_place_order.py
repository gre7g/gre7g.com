"""
Test order submission

POST /api/v1/order turns the user's cart into a PayPal OrderRequest and returns PayPal's response so the client can send
the buyer off to approve payment. The PayPal SDK is replaced with lightweight fakes: each SDK model class becomes a
MockObject that records its constructor arguments as a dict, so the order request the handler builds (and audit logs)
can be compared against a plain nested dictionary.
"""

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
# What the fake PayPal client returns from create_order(); the handler should pass it straight back to the client
CREATED_ORDER = {
    "id": "1234",
    "links": [{"href": "url", "method": "GET", "rel": "verify"}],
    "status": "processing",
}


@dataclass
class MockObject:
    """
    Stand-in for a PayPal SDK model class

    Calling it (i.e. "constructing" the model) returns a dict of the class name and arguments instead of a real object.
    """

    name: str
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)

    def __call__(self, *args, **kwargs):
        """Return a description of the "constructed" object"""
        return {"name": self.name, "args": args, "kwargs": kwargs}


class MockSdkClient(MockObject):
    """
    Stand-in for PaypalServersdkClient

    Constructing it returns a client whose "orders" controller is this instance, so client.orders.create_order() lands
    in create_order() below.
    """

    def __call__(self, *args, **kwargs):
        """Return a fake client wired to this instance's orders controller"""
        obj = MockSdkClient("MockSdkClient", args, kwargs)
        obj.orders = self  # noqa
        return obj

    @staticmethod
    def create_order(*_args):
        """Pretend PayPal accepted the order"""
        return Mock(body=CREATED_ORDER)


class TestPlaceOrder(BaseTestCase):
    """Test order submission"""

    @NO_CLOUD
    @patch("lambda_base.PaypalServersdkClient")
    def test_logged_out_download(self, paypal_serversdk_client) -> None:
        """Should not be able to order digital downloads when logged out"""
        # The guest cart contains an audiobook, so the handler should refuse before ever reaching PayPal
        cart, cart_dict = self.guest_cart_data()
        with self.create_records([(self.carts_table, cart)]):
            response = self.post(
                "/api/v1/order",
                guest_user="guest1_id",
                json={},
            )
            assert response.status_code == HTTPStatus.UNAUTHORIZED

    # Test locally. Can't patch functions in the cloud.
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
        # Swap the patched SDK classes for MockObjects so the order request is captured as plain data (the @patch
        # decorators restore the real classes after the test). APIHelper.to_dictionary is patched to the identity
        # function, so what gets audit logged is exactly what the MockObjects returned.
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
            [(self.carts_table, cart), (self.products_table, self.OUT_OF_STOCK1), (self.products_table, self.PRODUCT2)]
        ):
            # p1 is out of stock, but the order should still go to PayPal; we just get warned
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
                # The OrderRequest, as rendered by MockObject, for a cart holding PRODUCT1 and PRODUCT2: $32.48 of items
                # plus $5.99 shipping, with "123-456" as the reference ID (from the patched uuid1)
                "order_request": {
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
                },
            }
            assert self.obj_in_audit_objects(needle, objects)
        finally:
            self.delete_audit_objects(objects)

    # Test locally. Can't patch functions in the cloud.
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
        # Same SDK fakes as test_stock_problem
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
        cart, cart_dict = self.guest_cart_no_downloads()
        with self.create_records(
            [(self.carts_table, cart), (self.products_table, self.PRODUCT1), (self.products_table, self.PRODUCT2)]
        ):
            response = self.post(
                "/api/v1/order",
                guest_user="guest1_id",
                json={},
            )
            assert response.status_code == HTTPStatus.CREATED
            assert response.json() == CREATED_ORDER

        # Check audit log too
        objects = self.get_all_audit_objects()
        try:
            needle = {
                "event": "place_order",
                "user_id": None,
                "guest_id": "guest1_id",
                # The OrderRequest, as rendered by MockObject, for a cart holding PRODUCT4: $36.98 of items plus $5.99
                # shipping, with "123-456" as the reference ID (from the patched uuid1)
                "order_request": {
                    "args": [
                        "CAPTURE",
                        [
                            {
                                "args": [
                                    {
                                        "args": [
                                            "USD",
                                            "42.97",
                                            {
                                                "args": [
                                                    {"args": ["USD", "36.98"], "kwargs": {}, "name": "Money"},
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
                                        }
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

    # Test locally. Can't patch functions in the cloud.
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
        # Same SDK fakes as test_stock_problem
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
            # The audiobook is categorized as DIGITAL_GOODS; shipping is still charged because of the paperback. The
            # item total is $15.99 + 2 x $18.49 = $52.97.
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
