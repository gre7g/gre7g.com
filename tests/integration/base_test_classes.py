"""
Base class for integration tests

Extends lib.local.integration_base.BaseTestCase (which handles talking to the API, simulated or deployed, and setting up
the DynamoDB tables) with shared product/cart/order fixtures and helpers for inspecting the S3 audit log.
"""

import boto3
from datetime import datetime, UTC
import json
import os
from typing import Any

from database import Cart, UserId, Product, ProductId, Order, OrderId, Timestamp, Filename
from lib.local import integration_base

# Types:
AuditObj = dict[str, Any]


class BaseTestCase(integration_base.BaseTestCase):
    """
    Base class for integration tests

    Each Product constant is paired with a P_DICT constant holding the JSON the API is expected to return for it, so
    tests can seed DynamoDB with the object and compare responses against the dictionary.
    """

    # Zero-quantity versions of PRODUCT1/PRODUCT4. They share product IDs with the in-stock versions so that a cart
    # holding PRODUCT1/PRODUCT4 can be checked against inventory that has run dry.
    OUT_OF_STOCK1 = Product(
        "Skeleton Crew", "--", "aa", "books/skeleton-crew", ProductId("p1"), 0, 13.99, media="paperback"
    )
    OUT_OF_STOCK4 = Product(
        "Long Way Home", "--", "dd", "books/long-way-home", ProductId("p2"), 0, 18.49, media="paperback"
    )
    # Physical (paperback) items, one in stock each
    PRODUCT1 = Product("Skeleton Crew", "--", "aa", "books/skeleton-crew", ProductId("p1"), 1, 13.99, media="paperback")
    P_DICT1 = {
        "name": "Skeleton Crew",
        "short_desc": "--",
        "description": "aa",
        "listing_path": "books/skeleton-crew",
        "product_id": "p1",
        "quantity": 1,
        "cost_per": 13.99,
        "images": [],
        "downloads": {},
        "media": "paperback",
        "status": "available",
        "parent_id": None,
        "child_ids": [],
    }
    PRODUCT2 = Product("Long Way Home", "--", "bb", "books/long-way-home", ProductId("p2"), 1, 18.49, media="paperback")
    P_DICT2 = {
        "name": "Long Way Home",
        "short_desc": "--",
        "description": "bb",
        "quantity": 1,
        "cost_per": 18.49,
        "listing_path": "books/long-way-home",
        "product_id": "p2",
        "images": [],
        "downloads": {},
        "media": "paperback",
        "status": "available",
        "parent_id": None,
        "child_ids": [],
    }
    # Digital item: the download value starts as None and is replaced with a signed URL when an order is fetched
    PRODUCT3 = Product(
        "Small World",
        "--",
        "cc",
        "books/small-world",
        ProductId("p3"),
        1,
        15.99,
        downloads={Filename("test.zip"): None},
        media="audiobook",
    )
    P_DICT3 = {
        "name": "Small World",
        "short_desc": "--",
        "description": "cc",
        "quantity": 1,
        "cost_per": 15.99,
        "listing_path": "books/small-world",
        "product_id": "p3",
        "images": [],
        "downloads": {"test.zip": None},
        "media": "audiobook",
        "status": "available",
        "parent_id": None,
        "child_ids": [],
    }
    # Same product ID as PRODUCT2 but a different description and quantity, so merging a cart holding PRODUCT4 into one
    # holding PRODUCT2 shows which version wins
    PRODUCT4 = Product("Long Way Home", "--", "dd", "books/long-way-home", ProductId("p2"), 2, 18.49, media="paperback")
    P_DICT4 = {
        "name": "Long Way Home",
        "short_desc": "--",
        "description": "dd",
        "quantity": 2,
        "cost_per": 18.49,
        "listing_path": "books/long-way-home",
        "product_id": "p2",
        "images": [],
        "downloads": {},
        "media": "paperback",
        "status": "available",
        "parent_id": None,
        "child_ids": [],
    }

    def cart_data(self):
        """Return a logged-in user's all-physical cart (PRODUCT1, PRODUCT2) and its expected JSON"""
        return (
            Cart(UserId(self.regular_user.user_id), [self.PRODUCT1, self.PRODUCT2]),
            {"products": [self.P_DICT1, self.P_DICT2]},
        )

    def digital_cart_data(self):
        """Return a logged-in user's mixed digital/physical cart (PRODUCT3, PRODUCT4) and its expected JSON"""
        return (
            Cart(UserId(self.regular_user.user_id), [self.PRODUCT3, self.PRODUCT4]),
            {"products": [self.P_DICT3, self.P_DICT4]},
        )

    def guest_cart_data(self):
        """Return a guest's mixed digital/physical cart (PRODUCT3, PRODUCT4) and its expected JSON"""
        return (
            Cart(UserId("guest1_id"), [self.PRODUCT3, self.PRODUCT4]),
            {"products": [self.P_DICT3, self.P_DICT4]},
        )

    def guest_cart_no_downloads(self):
        """Return a guest's all-physical cart (PRODUCT4 only) and its expected JSON"""
        return (
            Cart(UserId("guest1_id"), [self.PRODUCT4]),
            {"products": [self.P_DICT4]},
        )

    def order_data(self):
        """
        Return two orders for the regular user and the expected JSON for the order history

        The second order includes a digital download and a discount. The cost fields are arbitrary values rather than
        sums of the product prices; the handlers echo them back without recalculating.
        """
        order1 = Order(
            UserId(self.regular_user.user_id),
            [self.PRODUCT1],
            13.99,
            5.00,
            18.99,
            "abc",
            0.00,
            OrderId("order1_id"),
            Timestamp("recently"),
        )
        order2 = Order(
            UserId(self.regular_user.user_id),
            [self.PRODUCT3, self.PRODUCT4],
            18.49,
            5.00,
            21.49,
            "def",
            -2.00,
            OrderId("order2_id"),
            Timestamp("long ago"),
        )
        order_dict = {
            "orders": [
                {
                    "products": [self.P_DICT1],
                    "subtotal_cost": 13.99,
                    "discount": 0.00,
                    "shipping_cost": 5.00,
                    "total_cost": 18.99,
                    "order_id": "order1_id",
                    "timestamp": "recently",
                    "notes": [],
                    "transaction_id": "abc",
                },
                {
                    "products": [self.P_DICT3, self.P_DICT4],
                    "subtotal_cost": 18.49,
                    "discount": -2.00,
                    "shipping_cost": 5.00,
                    "total_cost": 21.49,
                    "order_id": "order2_id",
                    "timestamp": "long ago",
                    "notes": [],
                    "transaction_id": "def",
                },
            ]
        }
        return [order1, order2], order_dict

    def get_all_audit_objects(self) -> dict[str, AuditObj]:
        """
        Fetch every custom audit log object written this month, keyed by S3 key

        Audit objects are stored under custom/YYYY-MM..., so only the current month's prefix is listed.
        """
        now = datetime.now(UTC)
        s3 = boto3.client("s3")

        # Get a list of keys (a single list call; assumes fewer than 1000 objects so no pagination is needed)
        response = s3.list_objects_v2(Bucket=self.audit_log, Prefix=f"custom/{now.strftime('%Y-%m')}")
        keys = [item["Key"] for item in response["Contents"]]

        # Get objects
        objects = {}
        for key in keys:
            body = s3.get_object(Bucket=self.audit_log, Key=key)["Body"]
            objects[key] = json.loads(body.read())
        return objects

    @staticmethod
    def obj_in_audit_objects(needle: AuditObj, haystack: dict[str, AuditObj]) -> bool:
        """
        Return True if any audit object contains all the key/value pairs in needle

        This is a subset match, so audit fields the test doesn't care about (timestamps, etc.) are ignored.
        """
        for obj in haystack.values():
            if all(obj.get(key) == value for key, value in needle.items()):
                return True
        return False

    def delete_audit_objects(self, objects: dict[str, AuditObj]) -> None:
        """Delete the given audit log objects so later tests start from a clean log"""
        # NEVER CLEAR THE PRODUCTION AUDIT LOG!
        if os.getenv("STACK-NAME", "gre7g-com-PROD").endswith("-PROD"):
            raise Exception("Cannot clear the production audit log")

        s3 = boto3.client("s3")
        s3.delete_objects(Bucket=self.audit_log, Delete={"Objects": [{"Key": key} for key in objects]})
