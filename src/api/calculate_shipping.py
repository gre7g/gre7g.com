"""
Calculate shipping

POST /api/v1/cart/shipping. Quotes the shipping charge for the caller's cart and tells the client whether the shopper
must log in before checking out. Mirrors the rules place_order applies when the order is actually built.

REQUIRES: CartsRead
"""

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext
import logging
import os
from typing import Any

from database import Cart
from lambda_base import LambdaBase, PHYSICAL_SHIPPING, ProductMix

# Constants:
LOG = Logger(__name__) if os.getenv("AWS_LAMBDA_FUNCTION_NAME") else logging.getLogger(__name__)


class CalculateShipping(LambdaBase):
    """Calculate shipping"""

    def handler(self, event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
        """Calculate shipping

        Request: Authorization bearer token and/or `x-guest-id` header.
        Response: {"shipping_cost": <float>, "user_status": "logged_in" | "must_log_in" | "may_log_in"}"""
        # A logged-in identity takes precedence over the guest ID
        user_id = self.user_id or self.guest_id

        assert user_id
        assert self.carts_table

        cart = Cart.get(self.carts_table, user_id)
        mix = self.get_product_mix(cart.products)

        # Note: The shopping cart is user-provided, so it could theoretically be tampered with. The user could say that
        # their paperback are digital downloads, so this script will report that they don't have to pay any shipping.
        # They could say that their digital downloads are paperbacks so they don't need to log in to buy them.
        #
        # I GUESS?!
        #
        # Though they could do this, it would only change how things are listed on their check-out page. They would,
        # essentially, just be fooling themselves. When the actual purchase is made, we make these determinations based
        # on data they cannot modify.

        # Shipping is a flat rate charged once if anything in the cart is a physical item; digital-only carts ship free
        shipping_cost = PHYSICAL_SHIPPING if mix in [ProductMix.ALL_PHYSICAL, ProductMix.MIX_OF_TYPES] else 0.00
        if self.user_id:
            user_status = "logged_in"
        else:
            # Digital downloads are tied to an account (so they can be re-downloaded from the order history), so a
            # guest must log in if the cart contains any. Physical-only carts may be bought as a guest.
            user_status = "must_log_in" if mix in [ProductMix.ALL_DIGITAL, ProductMix.MIX_OF_TYPES] else "may_log_in"

        return {"shipping_cost": shipping_cost, "user_status": user_status}


lambda_handler = CalculateShipping.lambda_handler()
