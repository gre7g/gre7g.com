"""Various utilities used in accessing DynamoDB tables"""

from aws_lambda_powertools import Logger
from dataclasses import dataclass, field
from datetime import datetime, UTC
from decimal import Decimal
from enum import auto, StrEnum
import logging
import os
from types_boto3_dynamodb.service_resource import Table as DynamoDBTable
from typing import Any, Self, NewType
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
