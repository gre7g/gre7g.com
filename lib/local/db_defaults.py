from types_boto3_dynamodb.service_resource import Table as DynamoDBTable

from database import Product, Cart, UserId, ProductStatus, Order, OrderId, Timestamp
from lib.local.inventory import PRODUCTS


def write_default_data_to_db(user_id: UserId, carts_table: DynamoDBTable, orders_table: DynamoDBTable) -> None:

    def find(product_id: str) -> Product:
        for item in PRODUCTS:
            if item.product_id == product_id:
                return item
        assert False

    sc = find("kc1-paperback")
    sc.quantity = 1
    lwh = find("lwh-ebook")
    lwh.quantity = 1
    pin = find("hc-pin")
    pin.quantity = 1
    carts = [
        Cart(user_id, [sc, lwh, pin]),
    ]
    carts_table.SECRET_OVERRIDE = True  # type: ignore [attr-defined]
    for cart in carts:
        cart.put(carts_table)
    carts_table.SECRET_OVERRIDE = False  # type: ignore [attr-defined]

    rl = find("tm1-paperback")
    rl.quantity = 1
    rl.status = ProductStatus.SHIPPED
    eg = find("tm2-paperback")
    eg.quantity = 1
    eg.status = ProductStatus.SHIPPED
    subtotal1 = rl.cost_per = eg.cost_per
    nlb1 = find("kc3.5-audiobook")
    nlb1.quantity = 1
    nlb1.status = ProductStatus.REFUNDED
    nlb2 = find("kc3.5-ebook")
    nlb2.quantity = 2
    nlb2.status = ProductStatus.DOWNLOADED

    orders = [
        Order(
            user_id,
            [rl, eg],
            subtotal1,
            5.99,
            subtotal1 + 5.99,
            "abc",
            0.00,
            OrderId("order1_id"),
            Timestamp("2026-01-17T10:15:00.000Z"),
        ),
        Order(
            user_id,
            [nlb1, nlb2],
            nlb1.cost_per + nlb2.cost_per,
            0.00,
            nlb1.cost_per + nlb2.cost_per,
            "def",
            0.00,
            OrderId("order2_id"),
            Timestamp("2026-03-21T17:59:00.000Z"),
            ["8:25am 3/22/2026: This is a placeholder item, so I'm refunding your item. Sorry about that!"],
        ),
    ]
    orders_table.SECRET_OVERRIDE = True  # type: ignore [attr-defined]
    for order in orders:
        order.put(orders_table)
    carts_table.SECRET_OVERRIDE = False  # type: ignore [attr-defined]
