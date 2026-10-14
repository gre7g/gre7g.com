"""View wares"""

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext
import logging
import os
from typing import Any

from gre7g_utils import LambdaBase, Product

# Constants:
LOG = Logger(__name__) if os.getenv("AWS_LAMBDA_FUNCTION_NAME") else logging.getLogger(__name__)


class GetProducts(LambdaBase):
    """View wares"""

    def handler(self, event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
        """View wares"""
        assert self.products_table

        response = self.products_table.scan()
        products = [Product.from_dict(product).to_client_dict() for product in response["Items"]]

        return {"products": products}


lambda_handler = GetProducts.lambda_handler()
