"""Base class for integration tests"""

import boto3
from datetime import datetime, UTC
import json
from typing import Any

from gre7g_utils import Cart, UserId, Product, ProductId, Order, OrderId, Timestamp
import integration_base

# Types:
AuditObj = dict[str, Any]


class BaseTestCase(integration_base.BaseTestCase):
    """Base class for integration tests"""

    PRODUCT1 = Product("Skeleton Crew", "aa", "books/skeleton-crew", ProductId("kc1"), 1, 13.99)
    P_DICT1 = {
        "name": "Skeleton Crew",
        "description": "aa",
        "listing_path": "books/skeleton-crew",
        "product_id": "kc1",
        "quantity": 1,
        "cost_per": 13.99,
        "downloads": [],
        "status": "available",
        "parent_id": None,
        "child_ids": [],
    }
    PRODUCT2 = Product("Long Way Home", "bb", "books/long-way-home", ProductId("lwh"), 1, 18.49)
    P_DICT2 = {
        "name": "Long Way Home",
        "description": "bb",
        "quantity": 1,
        "cost_per": 18.49,
        "listing_path": "books/long-way-home",
        "product_id": "lwh",
        "downloads": [],
        "status": "available",
        "parent_id": None,
        "child_ids": [],
    }
    PRODUCT3 = Product("Small World", "cc", "books/small-world", ProductId("kc2"), 1, 15.99, ["test.zip"])
    P_DICT3 = {
        "name": "Small World",
        "description": "cc",
        "quantity": 1,
        "cost_per": 15.99,
        "listing_path": "books/small-world",
        "product_id": "kc2",
        "downloads": ["test.zip"],
        "status": "available",
        "parent_id": None,
        "child_ids": [],
    }
    PRODUCT4 = Product("Long Way Home", "dd", "books/long-way-home", ProductId("lwh"), 2, 18.49)
    P_DICT4 = {
        "name": "Long Way Home",
        "description": "dd",
        "quantity": 2,
        "cost_per": 18.49,
        "listing_path": "books/long-way-home",
        "product_id": "lwh",
        "downloads": [],
        "status": "available",
        "parent_id": None,
        "child_ids": [],
    }

    def cart_data(self):
        """Return some cart data"""
        return (
            Cart(UserId(self.regular_user.user_id), [self.PRODUCT1, self.PRODUCT2]),
            {"products": [self.P_DICT1, self.P_DICT2]},
        )

    def guest_cart_data(self):
        """Return some cart additional data"""
        return (
            Cart(UserId("guest1_id"), [self.PRODUCT3, self.PRODUCT4]),
            {"products": [self.P_DICT3, self.P_DICT4]},
        )

    def order_data(self):
        """Return some order data"""
        order1 = Order(
            UserId(self.regular_user.user_id),
            [self.PRODUCT1],
            13.99,
            0.00,
            5.00,
            18.99,
            OrderId("order1_id"),
            Timestamp("recently"),
        )
        order2 = Order(
            UserId(self.regular_user.user_id),
            [self.PRODUCT3],
            18.49,
            -2.00,
            5.00,
            21.49,
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
                },
                {
                    "products": [self.P_DICT3],
                    "subtotal_cost": 18.49,
                    "discount": -2.00,
                    "shipping_cost": 5.00,
                    "total_cost": 21.49,
                    "order_id": "order2_id",
                    "timestamp": "long ago",
                    "notes": [],
                },
            ]
        }
        return [order1, order2], order_dict

    def get_all_audit_objects(self) -> dict[str, AuditObj]:
        now = datetime.now(UTC)
        s3 = boto3.client("s3")

        # Get a list of keys
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
        for obj in haystack.values():
            if all(obj.get(key) == value for key, value in needle.items()):
                return True
        return False

    def delete_audit_objects(self, objects: dict[str, AuditObj]) -> None:
        s3 = boto3.client("s3")
        s3.delete_objects(Bucket=self.audit_log, Delete={"Objects": [{"Key": key} for key in objects]})
