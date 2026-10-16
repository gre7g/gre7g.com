"""Download a file"""

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext
import boto3
import logging
import os
from typing import Any

from gre7g_utils import LambdaBase, AuthenticationRequired

# Constants:
LOG = Logger(__name__) if os.getenv("AWS_LAMBDA_FUNCTION_NAME") else logging.getLogger(__name__)
DOWNLOAD_WINDOW = 3600  # 1 hour authentication to download the files


class Download(LambdaBase):
    """Download a file"""

    AUTH_REQUIRED = AuthenticationRequired.USER

    def handler(self, event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
        """Download a file"""
        url = boto3.client("s3").generate_presigned_url(
            "get_object",
            Params={"Bucket": "gre7g-com-downloads", "Key": "test.zip"},
            ExpiresIn=3600,  # Link expires in 1 hour
        )
        LOG.info("succeeded", extra={"url": url, "params": self.path_parameters})
        return {"url": url}
        # assert self.orders_table
        # assert self.user_id
        #
        # order_id = self.path_parameters["order_id"]
        # product_id = self.path_parameters["product_id"]
        #
        # order = Order.get(self.orders_table, self.user_id, order_id)
        # for product in order.products:
        #     if product.product_id == product_id:
        #         parts = product.listing_path.split("/")
        #         filename = f"{parts[-1]}.zip"
        #         raise DownloadedFile(filename, Path(filename))
        #
        # assert False, "product not found"


lambda_handler = Download.lambda_handler()
