"""Download a file"""

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext
import logging
import os
from pathlib import Path
from typing import Any

from gre7g_utils import LambdaBase, DownloadedFile, Order

# Constants:
LOG = Logger(__name__) if os.getenv("AWS_LAMBDA_FUNCTION_NAME") else logging.getLogger(__name__)


class Download(LambdaBase):
    """Download a file"""

    def handler(self, event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
        """Download a file"""
        assert self.orders_table

        order_id = self.path_parameters["order_id"]
        product_id = self.path_parameters["product_id"]

        order = Order.get(self.orders_table, self.user_id, order_id)
        for product in order.products:
            if product.product_id == product_id:
                parts = product.listing_path.split("/")
                filename = f"{parts[-1]}.zip"
                raise DownloadedFile(filename, Path(filename))

        assert False, "product not found"


lambda_handler = Download.lambda_handler()
