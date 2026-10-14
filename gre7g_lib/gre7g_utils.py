"""Various utilities used in lambdas and testing"""

from abc import ABC, abstractmethod
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext
from base64 import b64decode
import boto3
from botocore.exceptions import ClientError
from dataclasses import dataclass, field
from datetime import datetime, UTC
from decimal import Decimal
from enum import auto, StrEnum
from http import HTTPStatus
import json
import logging
import os
from pathlib import Path
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


def currency(value: float) -> Decimal:
    return Decimal("%0.2f" % value)


class AuthenticationRequired(StrEnum):
    """Authentication required at the lambda level"""

    # Basic rights
    NONE = auto()
    ACTIVE_USER = auto()


class OrderStatus(StrEnum):
    """Order statuses"""

    PLACED = auto()
    CANCELED = auto()
    SHIPPED = auto()


class DownloadedFile(Exception):
    """Skip the normal handling and return this file for downloading"""

    def __init__(self, filename: str, path: Path, content_type: str = "application/zip") -> None:
        self.filename, self.path, self.content_type = filename, path, content_type


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
class AuditLog(Upgradeable):
    """A log of important events we don't want to lose"""

    content: dict[str, Any]
    timestamp: Timestamp = field(default_factory=lambda: Timestamp(datetime.now(UTC).isoformat()))
    version: int = TABLE_VERSION

    @classmethod
    def from_dict(cls, value_dict: dict[str, Any]) -> Self:
        """Generate an object from a dict"""
        value_dict = cls.upgrade(value_dict)
        timestamp = value_dict["timestamp"]
        content = value_dict["content"]
        assert isinstance(timestamp, str)
        assert isinstance(content, dict)
        return cls(content, Timestamp(timestamp))

    def to_dict(self) -> dict[str, Any]:
        """Convert the object to a dict"""
        content = json.loads(json.dumps(self.content), parse_float=Decimal)
        return {
            "content": content,
            "timestamp": self.timestamp,
            "version": TABLE_VERSION,
        }


@dataclass
class Product(Upgradeable):
    """A product for sale, sold, or in a shopping cart"""

    name: str
    quantity: int
    cost_per: float
    listing_path: str
    product_id: ProductId = field(default_factory=lambda: ProductId(uuid1().hex))
    version: int = TABLE_VERSION

    @classmethod
    def from_dict(cls, value_dict: dict[str, Any]) -> Self:
        """Generate an object from a dict"""
        value_dict = cls.upgrade(value_dict)
        name = value_dict["name"]
        quantity = value_dict["quantity"]
        cost_per = value_dict["cost_per"]
        listing_path = value_dict["listing_path"]
        product_id = value_dict["product_id"]
        assert isinstance(name, str)
        assert isinstance(quantity, int | Decimal)
        assert isinstance(cost_per, float | Decimal)
        assert isinstance(listing_path, str)
        assert isinstance(product_id, str)
        return cls(name, int(quantity), float(cost_per), listing_path, ProductId(product_id))

    def to_dict(self) -> dict[str, Any]:
        """Convert the object to a dict"""
        return {
            "name": self.name,
            "quantity": self.quantity,
            "cost_per": currency(self.cost_per),
            "listing_path": self.listing_path,
            "product_id": self.product_id,
            "version": TABLE_VERSION,
        }

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
    discount: float
    shipping_cost: float
    total_cost: float
    order_id: OrderId = field(default_factory=lambda: OrderId(uuid1().hex))
    downloads: dict[str, bool] = field(default_factory=dict)
    timestamp: Timestamp = field(default_factory=lambda: Timestamp(datetime.now(UTC).isoformat()))
    status: OrderStatus = OrderStatus.PLACED
    version: int = TABLE_VERSION

    @classmethod
    def from_dict(cls, value_dict: dict[str, Any]) -> Self:
        """Generate an object from a dict"""
        value_dict = cls.upgrade(value_dict)
        user_id = value_dict["user_id"]
        products = value_dict["products"]
        subtotal_cost = value_dict["subtotal_cost"]
        discount = value_dict["discount"]
        shipping_cost = value_dict["shipping_cost"]
        total_cost = value_dict["total_cost"]
        order_id = value_dict["order_id"]
        downloads = value_dict["downloads"]
        timestamp = value_dict["timestamp"]
        status = value_dict["status"]
        assert isinstance(user_id, str)
        assert isinstance(products, list)
        assert isinstance(subtotal_cost, float | Decimal)
        assert isinstance(discount, float | Decimal)
        assert isinstance(shipping_cost, float | Decimal)
        assert isinstance(total_cost, float | Decimal)
        assert isinstance(order_id, str)
        assert isinstance(downloads, dict)
        assert isinstance(timestamp, str)
        assert isinstance(status, str)
        product_list = [product.from_dict(product) for product in products]
        return cls(
            UserId(user_id),
            product_list,
            float(subtotal_cost),
            float(discount),
            float(shipping_cost),
            float(total_cost),
            OrderId(order_id),
            downloads,
            Timestamp(timestamp),
            OrderStatus(status),
            TABLE_VERSION,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert the object to a dict"""
        products = [product.to_dict() for product in self.products]
        for product in products:
            del product["version"]
        return {
            "user_id": self.user_id,
            "products": products,
            "subtotal_cost": currency(self.subtotal_cost),
            "discount": currency(self.discount),
            "shipping_cost": currency(self.shipping_cost),
            "total_cost": currency(self.total_cost),
            "order_id": self.order_id,
            "downloads": self.downloads,
            "timestamp": self.timestamp,
            "status": self.status.name,
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

    audit_log_table: DynamoDBTable | None = None
    products_table: DynamoDBTable | None = None
    carts_table: DynamoDBTable | None = None
    orders_table: DynamoDBTable | None = None

    path_parameters: dict = field(default_factory=dict)
    user_id: UserId | None = None
    guest_id: UserId | None = None

    AUTH_REQUIRED = AuthenticationRequired.NONE

    @abstractmethod
    def handler(self, event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
        """Overload this function with your handler code"""
        raise NotImplementedError

    def extract_user_id(self, event: dict[str, Any]) -> None:
        """Decode user sub from JWT bearer token if present, without verifying signature"""
        self.user_id = None
        token = (event.get("headers") or {}).get("authorization", "")
        try:
            if token.startswith("Bearer "):
                payload_b64 = token.split(".")[1]
                payload_b64 += "=" * (-len(payload_b64) % 4)
                claims = json.loads(b64decode(payload_b64))
                self.user_id = UserId(claims["sub"])
        except Exception:
            pass

    def wrapper(self, event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
        """Wrapper around the handler than takes care of parameters, privileges, and error handling"""
        try:
            self.path_parameters = event.get("pathParameters") or {}
            self.extract_user_id(event)
            self.guest_id = event.get("headers", {}).get("x-guest-id")

            if (self.AUTH_REQUIRED == AuthenticationRequired.ACTIVE_USER) and not self.user_id:
                raise PermissionError()

            status = HTTPStatus.OK
            body = self.handler(event=event, context=context)

        except ClientError as error:
            LOG.exception(error)
            if error.response["Error"]["Code"] == "ConditionalCheckFailedException":
                status = HTTPStatus.BAD_REQUEST
                body = {"message": "failed update condition"}
            else:
                status = HTTPStatus.INTERNAL_SERVER_ERROR
                body = {"message": error.response["Error"]["Message"]}

        except PermissionError:
            LOG.error("Unauthenticated")
            status = HTTPStatus.FORBIDDEN
            body = {"message": "Forbidden"}

        except KeyError as error:
            LOG.exception("key error")
            status = HTTPStatus.BAD_REQUEST
            body = {"message": str(error)}

        except DownloadedFile as file_details:
            with file_details.path.open("rb") as file_obj:
                data = file_obj.read()
            return {
                "statusCode": HTTPStatus.OK,
                "headers": {
                    "content-type": file_details.content_type,
                    "content-disposition": f'attachment; filename="{file_details.filename}"',
                    "content-length": len(data),
                },
                "body": data,
            }

        except Exception as error:
            LOG.exception("Unhandled exception")
            status = HTTPStatus.INTERNAL_SERVER_ERROR
            body = {"message": str(error)}

        return {
            "statusCode": status,
            "headers": {"content-type": "application/json"},
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
            audit_log_table = cls.get_table("AUDIT_LOG_TABLE")
            products_table = cls.get_table("PRODUCTS_TABLE")
            carts_table = cls.get_table("CARTS_TABLE")
            orders_table = cls.get_table("ORDERS_TABLE")
            return cls(audit_log_table, products_table, carts_table, orders_table).wrapper
        except:
            LOG.exception("loading object failed")
            return None
