"""Base class for integration tests"""

from gre7g_utils import Cart, UserId, Product, ProductId, Order, OrderId, Timestamp
import integration_base


class BaseTestCase(integration_base.BaseTestCase):
    """Base class for integration tests"""

    PRODUCT1 = Product("Skeleton Crew", 1, 13.99, "books/skeleton-crew", ProductId("kc1"))
    P_DICT1 = {
        "name": "Skeleton Crew",
        "quantity": 1,
        "cost_per": 13.99,
        "listing_path": "books/skeleton-crew",
        "product_id": "kc1",
    }
    PRODUCT2 = Product("Long Way Home", 1, 18.49, "books/long-way-home", ProductId("lwh"))
    P_DICT2 = {
        "name": "Long Way Home",
        "quantity": 1,
        "cost_per": 18.49,
        "listing_path": "books/long-way-home",
        "product_id": "lwh",
    }

    def cart_data(self):
        """Return some cart data"""
        return (
            Cart(UserId(self.regular_user.user_id), [self.PRODUCT1, self.PRODUCT2]),
            {"products": [self.P_DICT1, self.P_DICT2]},
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
            {},
            Timestamp("recently"),
        )
        order2 = Order(
            UserId(self.regular_user.user_id),
            [self.PRODUCT2],
            18.49,
            -2.00,
            5.00,
            21.49,
            OrderId("order2_id"),
            {},
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
                    "downloads": {},
                    "timestamp": "recently",
                    "status": "placed",
                },
                {
                    "products": [self.P_DICT2],
                    "subtotal_cost": 18.49,
                    "discount": -2.00,
                    "shipping_cost": 5.00,
                    "total_cost": 21.49,
                    "order_id": "order2_id",
                    "downloads": {},
                    "timestamp": "long ago",
                    "status": "placed",
                },
            ]
        }
        return [order1, order2], order_dict
