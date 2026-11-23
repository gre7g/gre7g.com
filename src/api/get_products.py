"""
View wares

GET /api/v1/products. Public product catalog; no authentication required.

REQUIRES: ProductsRead
"""

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext
import logging
import os
from typing import Any

from database import Product
from lambda_base import LambdaBase

# Constants:
LOG = Logger(__name__) if os.getenv("AWS_LAMBDA_FUNCTION_NAME") else logging.getLogger(__name__)


class GetProducts(LambdaBase):
    """View wares"""

    def handler(self, event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
        """View wares

        Request: no inputs.
        Response: {"products": [<client product dict>, ...]} for every row in the products table."""
        assert self.products_table

        # Full table scan. The catalog is small, so a single (unpaginated) scan is expected to return everything.
        response = self.products_table.scan()
        products = [Product.from_dict(product).to_client_dict() for product in response["Items"]]

        return {"products": products}


lambda_handler = GetProducts.lambda_handler()
