"""Various utilities used in accessing DynamoDB tables

Each table row is modeled as a dataclass with three representations:

* "to_dict()" -- the stored form. DynamoDB (via boto3) rejects Python floats, so money values are converted to
  "Decimal" with "currency()". A "version" field is added so rows can be migrated later.
* "to_client_dict()" -- the JSON-friendly form returned to the browser (floats, no version, no internal keys).
* "from_dict()" -- the reverse of "to_dict()". boto3 returns every DynamoDB number as "Decimal", so numeric
  fields are accepted as "Decimal" and converted back to "int"/"float".
"""

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
# NewType aliases are plain str at runtime; they exist so mypy catches mixed-up identifiers.
UserId = NewType("UserId", str)
OrderId = NewType("OrderId", str)
ProductId = NewType("ProductId", str)
Timestamp = NewType("Timestamp", str)
Filename = NewType("Filename", str)
PresignedUrl = NewType("PresignedUrl", str)

# Constants:
# Use the Powertools structured logger when running inside Lambda, plain stdlib logging otherwise (tests, local runs).
LOG = Logger(__name__) if os.getenv("AWS_LAMBDA_FUNCTION_NAME") else logging.getLogger(__name__)
TABLE_VERSION = 1  # Schema version written to every row; bump it and add an upgrade_N_to_N+1 method on schema changes
MAX_ITEMS_PER_BATCH = 100  # DynamoDB's limit on keys per BatchGetItem request


def currency(value: float) -> Decimal:
    """Convert a dollar amount to a Decimal rounded to cents, suitable for storing in DynamoDB

    Going through a formatted string (rather than "Decimal(value)") avoids carrying the float's binary
    representation error into the stored value, e.g. 5.99 becomes Decimal("5.99") rather than 5.9900000000000002131...
    """
    return Decimal("%0.2f" % value)


class ProductStatus(StrEnum):
    """Item statuses (stored as the lowercase member name)"""

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
    """Base class for a table row with a version number

    Subclasses migrate old rows by defining classmethods/staticmethods named "upgrade_<N>_to_<N+1>" that take and
    return a row dict. Missing steps are skipped, so only versions that actually changed the schema need one.
    """

    @classmethod
    def upgrade(cls, value_dict: dict[str, Any]) -> dict[str, Any]:
        """Upgrade a table row to the current version

        Args:
            value_dict: A row as read from DynamoDB ("version" may be a Decimal or missing).

        Returns:
            The row migrated to "TABLE_VERSION". The "version" key itself is not updated.

        Raises:
            AssertionError: If the row was written by a newer version of the code.
        """
        # Rows without a version are assumed current. int() is needed since DynamoDB returns numbers as Decimal.
        version = int(value_dict.get("version", TABLE_VERSION))
        assert version <= TABLE_VERSION, "Data is from a future version"
        # Apply each upgrade step in sequence (1->2, 2->3, ...) until the row is current.
        while version < TABLE_VERSION:
            upgrader = f"upgrade_{version}_to_{version + 1}"
            if hasattr(cls, upgrader):
                value_dict = getattr(cls, upgrader)(value_dict)
            version += 1
        return value_dict

    def to_dict(self) -> dict[str, Any]:
        """Convert the object to a dict in its DynamoDB storage form (subclasses must override)"""
        raise NotImplementedError  # pragma: no cover

    def put(self, db_table: DynamoDBTable) -> None:
        """Put object into table, unconditionally replacing any existing row with the same key"""
        assert db_table
        db_table.put_item(Item=self.to_dict())


@dataclass
class Product(Upgradeable):
    """A product for sale, sold, or in a shopping cart

    The same structure is used for catalog entries (products table, keyed by "product_id") and is embedded as a copy
    inside carts and orders, so an order keeps the price/description it was purchased with.
    """

    name: str
    short_desc: str
    description: str
    listing_path: str
    product_id: ProductId = field(default_factory=lambda: ProductId(str(uuid1())))
    quantity: int = 0
    cost_per: float = 0.00
    images: list[str] = field(default_factory=list)
    # S3 keys of downloadable files. Values are None until LambdaBase.sign_downloads() fills in short-lived URLs.
    downloads: dict[Filename, PresignedUrl | None] = field(default_factory=dict)
    media: str = ""  # e.g. "paperback" or "jewelry" (physical, see LambdaBase.physical_item) vs. digital formats
    status: ProductStatus = ProductStatus.AVAILABLE
    # Optional parent/child links between related product rows
    parent_id: str | None = None
    child_ids: list[str] = field(default_factory=list)
    version: int = TABLE_VERSION

    @classmethod
    def from_dict(cls, value_dict: dict[str, Any]) -> Self:
        """Generate an object from a dict (as read from DynamoDB)

        Raises:
            KeyError: If a field is missing.
            AssertionError: If a field has an unexpected type.
        """
        value_dict = cls.upgrade(value_dict)
        name = value_dict["name"]
        short_desc = value_dict["short_desc"]
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
        # Numbers come back from DynamoDB as Decimal, hence the extra allowed types (converted below).
        assert isinstance(name, str)
        assert isinstance(short_desc, str)
        assert isinstance(description, str)
        assert isinstance(listing_path, str)
        assert isinstance(product_id, str)
        assert isinstance(quantity, int | Decimal)
        assert isinstance(cost_per, float | int | Decimal)
        assert isinstance(images, list)
        assert isinstance(downloads, dict)
        assert isinstance(media, str)
        assert isinstance(status, str)
        assert isinstance(parent_id, str | None)
        assert isinstance(child_ids, list)
        return cls(
            name,
            short_desc,
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
            "short_desc": self.short_desc,
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
        """Convert the object to a dict in its DynamoDB storage form"""
        # Same as the client form, except the float price is replaced with a Decimal (boto3 rejects floats).
        return self.to_client_dict() | {"cost_per": currency(self.cost_per), "version": TABLE_VERSION}

    def to_key(self) -> dict[str, Any]:
        """Return the table key as a dict"""
        return {"product_id": self.product_id}

    @classmethod
    def get(cls, products_table: DynamoDBTable, product_id: ProductId) -> Self:
        """Get object from table

        Raises:
            KeyError: If no product exists with that ID ("get_item" omits "Item" when nothing matches).
        """
        assert products_table
        response = products_table.get_item(Key={"product_id": product_id})
        value_dict = response["Item"]
        return cls.from_dict(value_dict)


@dataclass
class Cart(Upgradeable):
    """A shopping cart, keyed by the owner's ID (a logged-in user's Cognito sub or a guest ID)"""

    user_id: UserId
    products: list[Product] = field(default_factory=list)
    version: int = TABLE_VERSION

    @classmethod
    def from_dict(cls, value_dict: dict[str, Any]) -> Self:
        """Generate an object from a dict (as read from DynamoDB)"""
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
        """Get object from table, or a new empty cart if the user doesn't have one yet

        Note that only parsing is protected; errors from "get_item" itself (e.g. a "ClientError") still propagate.
        """
        assert carts_table
        response = carts_table.get_item(Key={"user_id": user_id})
        # A missing "Item" means no cart exists. The bare except also turns an unparseable row into an empty cart
        # rather than failing the request.
        try:
            value_dict = response["Item"]
            cart = cls.from_dict(value_dict)
        except:
            cart = cls(user_id)
        return cart


@dataclass
class Order(Upgradeable):
    """An order, keyed by ("user_id", "order_id") so a user's orders can be queried together"""

    user_id: UserId
    products: list[Product]  # Snapshot of the cart's products at purchase time
    subtotal_cost: float
    shipping_cost: float
    total_cost: float
    transaction_id: str  # Payment processor (PayPal) reference
    discount: float = 0.00
    order_id: OrderId = field(default_factory=lambda: OrderId(str(uuid1())))
    timestamp: Timestamp = field(default_factory=lambda: Timestamp(datetime.now(UTC).isoformat()))
    notes: list[str] = field(default_factory=list)
    version: int = TABLE_VERSION

    @classmethod
    def from_dict(cls, value_dict: dict[str, Any]) -> Self:
        """Generate an object from a dict (as read from DynamoDB)

        Raises:
            KeyError: If a field is missing.
            AssertionError: If a field has an unexpected type.
        """
        value_dict = cls.upgrade(value_dict)
        user_id = value_dict["user_id"]
        products = value_dict["products"]
        subtotal_cost = value_dict["subtotal_cost"]
        shipping_cost = value_dict["shipping_cost"]
        total_cost = value_dict["total_cost"]
        transaction_id = value_dict["transaction_id"]
        discount = value_dict["discount"]
        order_id = value_dict["order_id"]
        timestamp = value_dict["timestamp"]
        notes = value_dict["notes"]
        # Money values are stored as Decimal (see currency()) and converted back to float below.
        assert isinstance(user_id, str)
        assert isinstance(products, list)
        assert isinstance(subtotal_cost, float | int | Decimal)
        assert isinstance(shipping_cost, float | int | Decimal)
        assert isinstance(total_cost, float | int | Decimal)
        assert isinstance(transaction_id, str)
        assert isinstance(discount, float | int | Decimal)
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
            transaction_id,
            float(discount),
            OrderId(order_id),
            Timestamp(timestamp),
            notes,
            TABLE_VERSION,
        )

    def to_client_dict(self) -> dict[str, Any]:
        """Convert the object to a client version's dict ("user_id" is omitted; the client already knows who it is)"""
        return {
            "products": [product.to_client_dict() for product in self.products],
            "subtotal_cost": float(self.subtotal_cost),
            "shipping_cost": float(self.shipping_cost),
            "total_cost": float(self.total_cost),
            "transaction_id": self.transaction_id,
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
            "transaction_id": self.transaction_id,
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
        """Get object from table

        Because the key includes "user_id", passing the caller's authenticated ID limits lookups to their own orders.

        Raises:
            KeyError: If no matching order exists ("get_item" omits "Item" when nothing matches).
        """
        assert order_table
        response = order_table.get_item(Key={"user_id": user_id, "order_id": order_id})
        value_dict = response["Item"]
        return cls.from_dict(value_dict)
