"""Various utilities used in lambdas and testing"""

from abc import ABC, abstractmethod
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext
import boto3
from botocore.exceptions import ClientError
from dataclasses import dataclass, field
from datetime import datetime, UTC
from decimal import Decimal
from enum import auto, StrEnum
from hashlib import sha3_256
import hmac
from http import HTTPStatus
import json
import jwt
import logging
import os
from paypalserversdk.configuration import Environment
from paypalserversdk.http.auth.o_auth_2 import ClientCredentialsAuthCredentials
from paypalserversdk.logging.configuration.api_logging_configuration import (
    LoggingConfiguration,
    RequestLoggingConfiguration,
    ResponseLoggingConfiguration,
)
from paypalserversdk.controllers.orders_controller import OrdersController
from paypalserversdk.paypal_serversdk_client import PaypalServersdkClient
from secrets import token_hex
from threading import Thread
from time import time
from types_boto3_dynamodb.service_resource import Table as DynamoDBTable
from typing import Any, Self, NewType, Callable
from uuid import uuid1

# Types:
UserId = NewType("UserId", str)
OrderId = NewType("OrderId", str)
ProductId = NewType("ProductId", str)
Timestamp = NewType("Timestamp", str)

# Constants:
LOG = Logger(__name__) if os.getenv("AWS_LAMBDA_FUNCTION_NAME") else logging.getLogger(__name__)
TABLE_VERSION = 1
MAX_ITEMS_PER_BATCH = 100
SIGN_ALGORITHMS = ["RS256", "RS384", "RS512", "ES256", "ES384", "ES512"]
CSRF_LIFETIME = 300  # 5 minutes
CSRF_HEADER = "x-csrf-token"
PAGE_EXPIRED = 419
PHYSICAL_SHIPPING = 5.99  # $5.99 for shipping paperbacks and jewelry in the US
CURRENCY = "USD"


def currency(value: float) -> Decimal:
    return Decimal("%0.2f" % value)


class AuthException(Exception):
    """Authentication required"""


class CSRFException(Exception):
    """CSRF expired or could not be authenticated"""


class AuthenticationRequired(StrEnum):
    """Authentication required at the lambda level"""

    # Basic rights
    NONE = auto()
    GUEST = auto()
    USER = auto()
    GUEST_OR_USER = auto()
    GUEST_AND_USER = auto()


class ProductStatus(StrEnum):
    """Item statuses"""

    AVAILABLE = auto()
    SOLD_OUT = auto()
    ORDERED = auto()
    CANCELED = auto()
    SHIPPED = auto()
    PARTIAL = auto()
    DOWNLOADED = auto()
    REFUNDED = auto()


class AuditLogEvent(StrEnum):
    """Audit log event types"""

    REGISTER_CLICK = auto()
    PLACE_ORDER = auto()
    CONFIRM_ORDER = auto()
    CART_MERGE = auto()


class ProductMix(StrEnum):
    """Describes a mix of products"""

    NONE = auto()
    ALL_DIGITAL = auto()
    ALL_PHYSICAL = auto()
    MIX_OF_TYPES = auto()


@dataclass
class Upgradeable:
    """Base class for a table row with a version number"""

    @classmethod
    def upgrade(cls, value_dict: dict[str, Any]) -> dict[str, Any]:
        """Upgrade a table row to the current version"""
        version = int(value_dict.get("version", TABLE_VERSION))
        assert version <= TABLE_VERSION, "Data is from a future version"
        while version < TABLE_VERSION:
            upgrader = f"upgrade_{version}_to_{version + 1}"
            if hasattr(cls, upgrader):
                value_dict = getattr(cls, upgrader)(value_dict)
            version += 1
        return value_dict

    def to_dict(self) -> dict[str, Any]:
        """Convert the object to a dict"""
        raise NotImplementedError

    def put(self, db_table: DynamoDBTable) -> None:
        """Put object into table"""
        assert db_table
        db_table.put_item(Item=self.to_dict())


@dataclass
class Product(Upgradeable):
    """A product for sale, sold, or in a shopping cart"""

    name: str
    description: str
    listing_path: str
    product_id: ProductId = field(default_factory=lambda: ProductId(str(uuid1())))
    quantity: int = 0
    cost_per: float = 0.00
    images: list[str] = field(default_factory=list)
    downloads: list[str] = field(default_factory=list)
    media: str = ""
    status: ProductStatus = ProductStatus.AVAILABLE
    parent_id: str | None = None
    child_ids: list[str] = field(default_factory=list)
    version: int = TABLE_VERSION

    @classmethod
    def from_dict(cls, value_dict: dict[str, Any]) -> Self:
        """Generate an object from a dict"""
        value_dict = cls.upgrade(value_dict)
        name = value_dict["name"]
        description = value_dict["description"]
        listing_path = value_dict["listing_path"]
        product_id = value_dict["product_id"]
        quantity = value_dict["quantity"]
        cost_per = value_dict["cost_per"]
        images = value_dict["images"]
        downloads = value_dict["downloads"]
        media = value_dict["media"]
        status = value_dict["status"]
        parent_id = value_dict["parent_id"]
        child_ids = value_dict["child_ids"]
        assert isinstance(name, str)
        assert isinstance(description, str)
        assert isinstance(listing_path, str)
        assert isinstance(product_id, str)
        assert isinstance(quantity, int | Decimal)
        assert isinstance(cost_per, float | Decimal)
        assert isinstance(images, list)
        assert isinstance(downloads, list)
        assert isinstance(media, str)
        assert isinstance(status, str)
        assert isinstance(parent_id, str | None)
        assert isinstance(child_ids, list)
        return cls(
            name,
            description,
            listing_path,
            ProductId(product_id),
            int(quantity),
            float(cost_per),
            images,
            downloads,
            media,
            ProductStatus(status),
            parent_id,
            child_ids,
        )

    def to_client_dict(self) -> dict[str, Any]:
        """Convert the object to a client version's dict"""
        return {
            "name": self.name,
            "description": self.description,
            "listing_path": self.listing_path,
            "product_id": self.product_id,
            "quantity": self.quantity,
            "cost_per": float(self.cost_per),
            "images": self.images,
            "downloads": self.downloads,
            "media": self.media,
            "status": self.status.value,
            "parent_id": self.parent_id,
            "child_ids": self.child_ids,
        }

    def to_dict(self) -> dict[str, Any]:
        """Convert the object to a dict"""
        return self.to_client_dict() | {"cost_per": currency(self.cost_per), "version": TABLE_VERSION}

    def to_key(self) -> dict[str, Any]:
        """Return the table key as a dict"""
        return {"product_id": self.product_id}

    @classmethod
    def get(cls, products_table: DynamoDBTable, product_id: ProductId) -> Self:
        """Get object from table"""
        assert products_table
        response = products_table.get_item(Key={"product_id": product_id})
        value_dict = response["Item"]
        return cls.from_dict(value_dict)


@dataclass
class Cart(Upgradeable):
    """A shopping cart"""

    user_id: UserId
    products: list[Product] = field(default_factory=list)
    version: int = TABLE_VERSION

    @classmethod
    def from_dict(cls, value_dict: dict[str, Any]) -> Self:
        """Generate an object from a dict"""
        value_dict = cls.upgrade(value_dict)
        user_id = value_dict["user_id"]
        products = [Product.from_dict(product) for product in value_dict["products"]]
        assert isinstance(user_id, str)
        assert isinstance(products, list)
        return cls(UserId(user_id), products)

    def to_client_dict(self) -> dict[str, Any]:
        """Convert the object to a client version's dict"""
        return {
            "user_id": self.user_id,
            "products": [product.to_client_dict() for product in self.products],
        }

    def to_dict(self) -> dict[str, Any]:
        """Convert the object to a dict"""
        return {
            "user_id": self.user_id,
            "products": [product.to_dict() for product in self.products],
            "version": TABLE_VERSION,
        }

    def to_key(self) -> dict[str, Any]:
        """Return the table key as a dict"""
        return {"user_id": self.user_id}

    @classmethod
    def get(cls, carts_table: DynamoDBTable, user_id: UserId) -> Self:
        """Get object from table"""
        assert carts_table
        response = carts_table.get_item(Key={"user_id": user_id})
        try:
            value_dict = response["Item"]
            cart = cls.from_dict(value_dict)
        except:
            cart = cls(user_id)
        return cart


@dataclass
class Order(Upgradeable):
    """An order"""

    user_id: UserId
    products: list[Product]
    subtotal_cost: float
    shipping_cost: float
    total_cost: float
    discount: float = 0.00
    order_id: OrderId = field(default_factory=lambda: OrderId(str(uuid1())))
    timestamp: Timestamp = field(default_factory=lambda: Timestamp(datetime.now(UTC).isoformat()))
    notes: list[str] = field(default_factory=list)
    version: int = TABLE_VERSION

    @classmethod
    def from_dict(cls, value_dict: dict[str, Any]) -> Self:
        """Generate an object from a dict"""
        value_dict = cls.upgrade(value_dict)
        user_id = value_dict["user_id"]
        products = value_dict["products"]
        subtotal_cost = value_dict["subtotal_cost"]
        shipping_cost = value_dict["shipping_cost"]
        total_cost = value_dict["total_cost"]
        discount = value_dict["discount"]
        order_id = value_dict["order_id"]
        timestamp = value_dict["timestamp"]
        notes = value_dict["notes"]
        assert isinstance(user_id, str)
        assert isinstance(products, list)
        assert isinstance(subtotal_cost, float | Decimal)
        assert isinstance(shipping_cost, float | Decimal)
        assert isinstance(total_cost, float | Decimal)
        assert isinstance(discount, float | Decimal)
        assert isinstance(order_id, str)
        assert isinstance(timestamp, str)
        assert isinstance(notes, list)
        product_list = [Product.from_dict(product) for product in products]
        return cls(
            UserId(user_id),
            product_list,
            float(subtotal_cost),
            float(shipping_cost),
            float(total_cost),
            float(discount),
            OrderId(order_id),
            Timestamp(timestamp),
            notes,
            TABLE_VERSION,
        )

    def to_client_dict(self) -> dict[str, Any]:
        """Convert the object to a client version's dict"""
        return {
            "products": [product.to_client_dict() for product in self.products],
            "subtotal_cost": float(self.subtotal_cost),
            "shipping_cost": float(self.shipping_cost),
            "total_cost": float(self.total_cost),
            "discount": float(self.discount),
            "order_id": self.order_id,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }

    def to_dict(self) -> dict[str, Any]:
        """Convert the object to a dict"""
        return {
            "user_id": self.user_id,
            "products": [product.to_dict() for product in self.products],
            "subtotal_cost": currency(self.subtotal_cost),
            "shipping_cost": currency(self.shipping_cost),
            "total_cost": currency(self.total_cost),
            "discount": currency(self.discount),
            "order_id": self.order_id,
            "timestamp": self.timestamp,
            "notes": self.notes,
            "version": TABLE_VERSION,
        }

    def to_key(self) -> dict[str, Any]:
        """Return the table key as a dict"""
        return {"user_id": self.user_id, "order_id": self.order_id}

    @classmethod
    def get(cls, order_table: DynamoDBTable, user_id: UserId, order_id: OrderId) -> Self:
        """Get object from table"""
        assert order_table
        response = order_table.get_item(Key={"user_id": user_id, "order_id": order_id})
        value_dict = response["Item"]
        return cls.from_dict(value_dict)


@dataclass
class LambdaBase(ABC):
    """Base class for lambdas"""

    products_table: DynamoDBTable | None = None
    carts_table: DynamoDBTable | None = None
    orders_table: DynamoDBTable | None = None
    secret_key: bytes = b""

    path_parameters: dict = field(default_factory=dict)
    user_id: UserId | None = None
    guest_id: UserId | None = None
    body: dict[str, Any] = field(default_factory=dict)

    AUTH_REQUIRED = AuthenticationRequired.NONE

    @abstractmethod
    def handler(self, event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
        """Overload this function with your handler code"""
        raise NotImplementedError

    def extract_user_id(self, event: dict[str, Any]) -> None:
        """Decode user sub from JWT bearer token if present, without verifying signature"""
        self.user_id = None
        auth_header = (event.get("headers") or {}).get("authorization", "")
        try:
            if auth_header.startswith("Bearer "):
                token = auth_header[7:]
                uri = os.environ.get("JWKS_URI")
                assert uri
                jwks_client = jwt.PyJWKClient(uri)
                signing_key = jwks_client.get_signing_key_from_jwt(token)
                claims = jwt.decode(
                    token,
                    signing_key.key,
                    algorithms=SIGN_ALGORITHMS,
                    issuer=os.environ.get("JWT_ISSUER"),
                    options={"verify_aud": False},
                )
                self.user_id = UserId(claims["sub"])
        except Exception:
            LOG.exception("failed to authenticate bearer token")

    def validate_csrf(self, csrf_header: str, source_ip: str) -> None:
        """Validate CSRF token"""
        if csrf_header:
            expiry, random_bits, signature = csrf_header.split("-")
            # We use time() and not monotonic() because the token could be generated on one machine and validated on
            # another.
            if float(expiry) >= time():
                csrf_token = f"{expiry}-{random_bits}-"
                message = f"{csrf_token}{source_ip}".encode("ascii")
                csrf_token += hmac.new(self.secret_key, message, sha3_256).hexdigest()
                if hmac.compare_digest(csrf_header, csrf_token):
                    return
        raise CSRFException()

    def wrapper(self, event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
        """Wrapper around the handler than takes care of parameters, privileges, and error handling"""
        http_dict = event["requestContext"]["http"]
        source_ip = http_dict["sourceIp"]
        try:
            self.path_parameters = event.get("pathParameters") or {}
            self.extract_user_id(event)
            headers = event.get("headers") or {}
            self.guest_id = headers.get("x-guest-id")
            if event.get("body"):
                self.body = json.loads(event["body"])
            if http_dict["method"] != "GET":
                self.validate_csrf(headers.get(CSRF_HEADER, ""), source_ip)

            match self.AUTH_REQUIRED:
                case AuthenticationRequired.NONE:
                    pass
                case AuthenticationRequired.GUEST:
                    if not self.guest_id:
                        raise PermissionError()
                case AuthenticationRequired.USER:
                    if not self.user_id:
                        raise PermissionError()
                case AuthenticationRequired.GUEST_OR_USER:
                    if not (self.guest_id or self.user_id):
                        raise PermissionError()
                case AuthenticationRequired.GUEST_AND_USER:
                    if not (self.guest_id and self.user_id):
                        raise PermissionError()
                case _:
                    raise Exception("unknown authentication requirement")

            status = HTTPStatus.CREATED if http_dict["method"] == "POST" else HTTPStatus.OK
            body = self.handler(event=event, context=context)

        except ClientError as error:
            LOG.exception(error)
            if error.response["Error"]["Code"] == "ConditionalCheckFailedException":
                status = HTTPStatus.BAD_REQUEST
                body = {"message": "failed update condition"}
            else:
                status = HTTPStatus.INTERNAL_SERVER_ERROR
                body = {"message": error.response["Error"]["Message"]}

        except AuthException:
            LOG.error("API function requires authentication and none provided")
            status = HTTPStatus.UNAUTHORIZED
            body = {"message": "Unauthorized"}

        except PermissionError:
            LOG.error("User lacks privileges for API function")
            status = HTTPStatus.FORBIDDEN
            body = {"message": "Forbidden"}

        except KeyError as error:
            LOG.exception("key error")
            status = HTTPStatus.BAD_REQUEST
            body = {"message": str(error)}

        except CSRFException:
            LOG.error("CSRF error")
            status = PAGE_EXPIRED  # type: ignore [assignment]
            body = {"message": "CSRF error"}

        except Exception as error:
            LOG.exception("Unhandled exception")
            status = HTTPStatus.INTERNAL_SERVER_ERROR
            body = {"message": str(error)}

        csrf_token = f"{int(time() + CSRF_LIFETIME)}-{token_hex()}-"
        message = f"{csrf_token}{source_ip}".encode("ascii")
        csrf_token += hmac.new(self.secret_key, message, sha3_256).hexdigest()
        return {
            "statusCode": status,
            "headers": {"content-type": "application/json", CSRF_HEADER: csrf_token},
            "body": json.dumps(body),
        }

    @staticmethod
    def get_table(env_name: str) -> DynamoDBTable | None:
        """Get a dynamodb table"""
        name = os.getenv(env_name)
        return boto3.resource("dynamodb").Table(name) if name else None

    @classmethod
    def lambda_handler(cls) -> Callable | None:
        """A convenience method for instantiating a Lambda handler"""
        try:
            products_table = cls.get_table("PRODUCTS_TABLE")
            carts_table = cls.get_table("CARTS_TABLE")
            orders_table = cls.get_table("ORDERS_TABLE")
            env_secret = os.getenv("CSRF_SECRET_KEY")
            secret_key = env_secret.encode("ascii") if env_secret else b""
            return cls(products_table, carts_table, orders_table, secret_key).wrapper
        except:
            LOG.exception("loading object failed")
            return None

    def audit_log(self, event: AuditLogEvent, **kwargs: Any) -> None:
        """Log an event to the audit log"""
        now = datetime.now(UTC)
        data = {"timestamp": now.isoformat(), "event": event.value, "user_id": self.user_id, "guest_id": self.guest_id}
        thread = Thread(
            target=boto3.client("s3").put_object,
            kwargs={
                "Bucket": os.environ["AUDIT_LOG_STORAGE"],
                "Key": f"custom/{now.strftime('%Y-%m')}/{str(uuid1())}.json",
                "Body": json.dumps(data | kwargs),
            },
            daemon=False,
        )
        thread.start()

    @staticmethod
    def get_cart_mix(cart: Cart) -> ProductMix:
        """Return what mix of items we have"""
        mix = ProductMix.NONE
        for product in cart.products:
            if product.media in ["paperback", "jewelry"]:
                mix = (
                    ProductMix.ALL_PHYSICAL
                    if mix in [ProductMix.NONE, ProductMix.ALL_PHYSICAL]
                    else ProductMix.MIX_OF_TYPES
                )
            else:
                mix = (
                    ProductMix.ALL_DIGITAL
                    if mix in [ProductMix.NONE, ProductMix.ALL_DIGITAL]
                    else ProductMix.MIX_OF_TYPES
                )
        return mix

    @staticmethod
    def get_paypal_controller() -> OrdersController:
        """Get an OrdersController from the PayPal SDK"""
        # PayPal connection is configured via environment variables so the codes won't be committed into git
        paypal_sandbox = os.getenv("PAYPAL_SANDBOX") == "True"
        paypal_client_id = os.getenv("PAYPAL_CLIENT_ID")
        paypal_client_secret = os.getenv("PAYPAL_CLIENT_SECRET")

        assert paypal_client_id
        assert paypal_client_secret

        # Configure logging
        log_config = LoggingConfiguration(
            log_level=logging.INFO if paypal_sandbox else logging.WARNING,
            mask_sensitive_headers=not paypal_sandbox,
            request_logging_config=RequestLoggingConfiguration(
                log_body=paypal_sandbox,
                log_headers=paypal_sandbox,
            ),
            response_logging_config=ResponseLoggingConfiguration(
                log_body=paypal_sandbox,
                log_headers=paypal_sandbox,
            ),
        )

        # Connect to PayPal
        paypal = PaypalServersdkClient(
            logging_configuration=log_config,
            environment=Environment.SANDBOX if paypal_sandbox else Environment.PRODUCTION,
            client_credentials_auth_credentials=ClientCredentialsAuthCredentials(
                paypal_client_id, paypal_client_secret
            ),
        )

        return paypal.orders


# TODO: put descriptions for paypal orders in db
