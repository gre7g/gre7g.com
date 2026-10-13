"""Base class for integration tests"""

from base64 import b64encode
import boto3
from contextlib import contextmanager
from enum import Enum, auto
import json
import logging
from openapi_core import OpenAPI
from openapi_core.contrib.requests import RequestsOpenAPIRequest, RequestsOpenAPIResponse
import os
from pathlib import Path
import requests
from typing import ClassVar, Generator, Any
from unittest import TestCase
from unittest.mock import Mock
import yaml

from boto3_hack import HackBoto, Table
from outputs import get_outputs_dict
from users import CognitoUser, REG_USER_ID, ADMIN_USER_ID, ADMIN_GROUP_NAME
from web_server import WebBrowser

# Constants:
LOG = logging.getLogger(__name__)
STACK_NAME = os.environ["STACK-NAME"]
RUN_LOCALLY = "LOCAL"
RUN_BRIEF = "BRIEF"
SERVER_PORT = 8000
TEMPLATE_YAML = Path(__file__).parents[1] / "template.yaml"

logging.basicConfig(level=logging.INFO)
for mouthy_log in ["boto3", "botocore", "urllib3"]:
    logging.getLogger(mouthy_log).setLevel(logging.WARNING)
if STACK_NAME in [RUN_LOCALLY, RUN_BRIEF]:
    HackBoto(TEMPLATE_YAML, {REG_USER_ID: [], ADMIN_USER_ID: [ADMIN_GROUP_NAME]}).apply_hack()  # type: ignore


class Validate(Enum):
    """On REST transactions, which portions of the dialogue should be validated?"""

    RQ_AND_RS = auto()
    RQ_ONLY = auto()
    RS_ONLY = auto()
    NOTHING = auto()


class BaseTestCase(TestCase):
    """Base class for integration tests"""

    initialized: ClassVar[bool] = False
    openapi: ClassVar[OpenAPI]
    stack_name: ClassVar[str]
    user_pool: ClassVar[str]
    user_pool_client: ClassVar[str]

    # Sam outputs
    api_endpoint: ClassVar[str]
    audit_log_name: ClassVar[str]
    carts_table_name: ClassVar[str]
    cloud_front_distribution: ClassVar[str]
    cognito_host_name: ClassVar[str]
    cognito_login_url: ClassVar[str]
    orders_table_name: ClassVar[str]
    products_table_name: ClassVar[str]
    user_pool: ClassVar[str]
    user_pool_client: ClassVar[str]
    website_url: ClassVar[str]

    # Database tables
    # audit_log: ClassVar[Any]
    carts_table: ClassVar[Any]
    orders_table: ClassVar[Any]
    products_table: ClassVar[Any]

    # Users
    regular_user: ClassVar[CognitoUser]

    @staticmethod
    def copy_outputs_to_members(stack_name: str) -> None:
        """Fetch the AWS SAM outputs from Cloudformation"""
        for key, value in get_outputs_dict(stack_name).items():
            setattr(BaseTestCase, key, value)

    def setup_openapi(self, yaml_path: Path) -> None:
        """Open the API specification"""
        if yaml_path.exists():
            spec = yaml.safe_load(yaml_path.read_text())
            spec["servers"] = [{"url": self.api_endpoint}]
            BaseTestCase.openapi = OpenAPI.from_dict(spec)

    def request(
        self,
        method: str,
        sub_url: str,
        auth_user: CognitoUser | None = None,
        guest_user: str | None = None,
        validate: Validate = Validate.RQ_AND_RS,
        **kwargs,
    ) -> requests.Response:
        """Make a request to the API under test"""
        url = f"{self.api_endpoint}/{sub_url.lstrip('/')}"
        kwargs.setdefault("headers", {}).update({"Content-Type": "application/json"})
        if auth_user:
            kwargs["headers"].update({"authorization": f"Bearer {auth_user.id_token}"})
        if guest_user:
            kwargs["headers"].update({"x-guest-id": guest_user})
        if STACK_NAME == RUN_BRIEF:
            content = json.dumps(kwargs.get("json", {}))
            result = boto3.resource.call_func(
                sub_url, method.lower(), kwargs.get("headers", {}), content, kwargs.get("params", {})
            )
            response = Mock(status_code=result["statusCode"])
            response.json.return_value = json.loads(result.get("body", "{}"))
        else:
            request = requests.Request(method, url, **kwargs)
            openapi_request = RequestsOpenAPIRequest(request)
            if validate in [Validate.RQ_AND_RS, Validate.RQ_ONLY]:
                self.openapi.validate_request(openapi_request)
            session = requests.Session()
            response = session.send(request.prepare())
            if validate in [Validate.RQ_AND_RS, Validate.RS_ONLY]:
                openapi_response = RequestsOpenAPIResponse(response)
                self.openapi.validate_response(openapi_request, openapi_response)
        return response

    def get(self, *args, **kwargs) -> requests.Response:
        """GET from the API"""
        return self.request("GET", *args, **kwargs)

    def put(self, *args, **kwargs) -> requests.Response:
        """PUT to the API"""
        return self.request("PUT", *args, **kwargs)

    def delete(self, *args, **kwargs) -> requests.Response:
        """DELETE from the API"""
        return self.request("DELETE", *args, **kwargs)

    def post(self, *args, **kwargs) -> requests.Response:
        """POST to the API"""
        return self.request("POST", *args, **kwargs)

    @staticmethod
    def record_in_database(table, key_exp, discards, record, result_column) -> str | None:
        """Find a record in the database"""
        response = table.query(KeyConditionExpression=key_exp)
        for item in response["Items"]:
            for discard in discards:
                item.pop(discard)
            if result_column in record:
                result = item[result_column]
            else:
                result = item.pop(result_column)
            if item == record:
                return result
        else:
            return None

    def setUp(self):
        """Test setup"""
        if not BaseTestCase.initialized:
            BaseTestCase.initialized = True

            path = Path(__file__).parents[1]
            if STACK_NAME in [RUN_LOCALLY, RUN_BRIEF]:
                if STACK_NAME == RUN_LOCALLY:
                    WebBrowser(SERVER_PORT).launch_daemon()
                BaseTestCase.api_endpoint = f"http://localhost:{SERVER_PORT}"
                bearer = b64encode(json.dumps({"sub": REG_USER_ID}).encode("ascii")).decode("ascii").rstrip("=")
                BaseTestCase.regular_user = Mock(id_token=f"something.{bearer}.something", user_id=REG_USER_ID)
                # bearer = b64encode(json.dumps({"sub": ADMIN_USER_ID}).encode("ascii")).decode("ascii").rstrip("=")
                # BaseTestCase.admin_user = Mock(id_token=f"something.{bearer}.something", user_id=ADMIN_USER_ID)
                BaseTestCase.audit_log_name = "AuditLog"
                BaseTestCase.carts_table_name = "CartsTable"
                BaseTestCase.products_table_name = "ProductsTable"
                BaseTestCase.orders_table_name = "OrdersTable"
            else:
                self.copy_outputs_to_members(STACK_NAME)
                # BaseTestCase.regular_user, BaseTestCase.admin_user = CognitoUser.create_users(
                BaseTestCase.regular_user = CognitoUser.create_users(self.user_pool, self.user_pool_client)

            self.setup_openapi(path / "api.yaml")
            dynamodb = boto3.resource("dynamodb")
            # BaseTestCase.audit_log = dynamodb.Table(self.audit_log_name)
            BaseTestCase.carts_table = dynamodb.Table(self.carts_table_name)
            BaseTestCase.orders_table = dynamodb.Table(self.orders_table_name)
            BaseTestCase.products_table = dynamodb.Table(self.products_table_name)

    @staticmethod
    @contextmanager
    def create_records(table_and_item: list[tuple]) -> Generator[list, None, None]:
        """Create records and clean them up when we're done"""
        Table.SECRET_OVERRIDE = True  # We might not have permission, but this is test infrastructure
        for table, item in table_and_item:
            item.put(table)
        Table.SECRET_OVERRIDE = False
        try:
            yield table_and_item
        finally:
            Table.SECRET_OVERRIDE = True
            for table, item in table_and_item:
                table.delete_item(Key=item.to_key())
            Table.SECRET_OVERRIDE = False
