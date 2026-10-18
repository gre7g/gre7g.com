"""Download a file"""

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext
import boto3
import logging
import os
from typing import Any

from gre7g_utils import LambdaBase, AuthenticationRequired, Order

# Constants:
LOG = Logger(__name__) if os.getenv("AWS_LAMBDA_FUNCTION_NAME") else logging.getLogger(__name__)
GLACIER_LAKE_BUCKET = "gre7g-com-downloads"
DOWNLOAD_WINDOW = 3600  # 1 hour authentication to download the files


class Download(LambdaBase):
    """Download a file"""

    AUTH_REQUIRED = AuthenticationRequired.USER

    def handler(self, event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
        """Download a file"""
        assert self.orders_table
        assert self.user_id

        order_id = self.path_parameters["order_id"]
        assert order_id

        # TODO: It's absolutely crucial that when the order is created, the items are taken from the product list and
        # not from the cart. The user can write whatever they want into the cart, and they could use to do various
        # malicious things such as adding more files to the download list and changing the costs.
        order = Order.get(self.orders_table, self.user_id, order_id)
        files = {}
        for product in order.products:
            for download in product.downloads:
                url = boto3.client("s3").generate_presigned_url(
                    "get_object",
                    Params={"Bucket": GLACIER_LAKE_BUCKET, "Key": download},
                    ExpiresIn=3600,  # Link expires in 1 hour
                )
                files[download] = url

        return {"files": files}


lambda_handler = Download.lambda_handler()
