"""Various utilities used in lambdas and testing"""

from abc import ABC, abstractmethod
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext
import boto3
from botocore.exceptions import ClientError
from dataclasses import dataclass, field
from enum import auto, StrEnum
from hashlib import sha3_256
import hmac
from http import HTTPStatus
import json
import jwt
import logging
import os
from paypalserversdk.configuration import Environment
from paypalserversdk.http.auth.o_auth_2 import ClientCredentialsAuthCredentials
from paypalserversdk.logging.configuration.api_logging_configuration import (
    LoggingConfiguration,
    RequestLoggingConfiguration,
    ResponseLoggingConfiguration,
)
from paypalserversdk.controllers.orders_controller import OrdersController
from paypalserversdk.paypal_serversdk_client import PaypalServersdkClient
from secrets import token_hex
from time import time
from types_boto3_dynamodb.service_resource import Table as DynamoDBTable
from typing import Any, Callable

from audit_log import AuditLogEvent, audit_log
from database import UserId, Cart

# Constants:
LOG = Logger(__name__) if os.getenv("AWS_LAMBDA_FUNCTION_NAME") else logging.getLogger(__name__)
SIGN_ALGORITHMS = ["RS256", "RS384", "RS512", "ES256", "ES384", "ES512"]
CSRF_LIFETIME = 300  # 5 minutes
CSRF_HEADER = "x-csrf-token"
PAGE_EXPIRED = 419
PHYSICAL_SHIPPING = 5.99  # $5.99 for shipping paperbacks and jewelry in the US
CURRENCY = "USD"


class AuthException(Exception):
    """Authentication required"""


class CSRFException(Exception):
    """CSRF expired or could not be authenticated"""


class AuthenticationRequired(StrEnum):
    """Authentication required at the lambda level"""

    # Basic rights
    NONE = auto()
    GUEST = auto()
    USER = auto()
    GUEST_OR_USER = auto()
    GUEST_AND_USER = auto()


class ProductMix(StrEnum):
    """Describes a mix of products"""

    NONE = auto()
    ALL_DIGITAL = auto()
    ALL_PHYSICAL = auto()
    MIX_OF_TYPES = auto()


@dataclass
class LambdaBase(ABC):
    """Base class for lambdas"""

    products_table: DynamoDBTable | None = None
    carts_table: DynamoDBTable | None = None
    orders_table: DynamoDBTable | None = None
    secret_key: bytes = b""

    path_parameters: dict = field(default_factory=dict)
    user_id: UserId | None = None
    guest_id: UserId | None = None
    body: dict[str, Any] = field(default_factory=dict)

    AUTH_REQUIRED = AuthenticationRequired.NONE

    @abstractmethod
    def handler(self, event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
        """Overload this function with your handler code"""
        raise NotImplementedError

    def extract_user_id(self, event: dict[str, Any]) -> None:
        """Decode user sub from JWT bearer token if present, without verifying signature"""
        self.user_id = None
        auth_header = (event.get("headers") or {}).get("authorization", "")
        try:
            if auth_header.startswith("Bearer "):
                token = auth_header[7:]
                uri = os.environ.get("JWKS_URI")
                assert uri
                jwks_client = jwt.PyJWKClient(uri)
                signing_key = jwks_client.get_signing_key_from_jwt(token)
                claims = jwt.decode(
                    token,
                    signing_key.key,
                    algorithms=SIGN_ALGORITHMS,
                    issuer=os.environ.get("JWT_ISSUER"),
                    options={"verify_aud": False},
                )
                self.user_id = UserId(claims["sub"])
        except Exception:
            LOG.exception("failed to authenticate bearer token")

    def validate_csrf(self, csrf_header: str, source_ip: str) -> None:
        """Validate CSRF token"""
        if csrf_header:
            expiry, random_bits, signature = csrf_header.split("-")
            # We use time() and not monotonic() because the token could be generated on one machine and validated on
            # another.
            if float(expiry) >= time():
                csrf_token = f"{expiry}-{random_bits}-"
                message = f"{csrf_token}{source_ip}".encode("ascii")
                csrf_token += hmac.new(self.secret_key, message, sha3_256).hexdigest()
                if hmac.compare_digest(csrf_header, csrf_token):
                    return
        raise CSRFException()

    def wrapper(self, event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
        """Wrapper around the handler than takes care of parameters, privileges, and error handling"""
        http_dict = event["requestContext"]["http"]
        source_ip = http_dict["sourceIp"]
        try:
            self.path_parameters = event.get("pathParameters") or {}
            self.extract_user_id(event)
            headers = event.get("headers") or {}
            self.guest_id = headers.get("x-guest-id")
            if event.get("body"):
                self.body = json.loads(event["body"])
            if http_dict["method"] != "GET":
                self.validate_csrf(headers.get(CSRF_HEADER, ""), source_ip)

            match self.AUTH_REQUIRED:
                case AuthenticationRequired.NONE:
                    pass
                case AuthenticationRequired.GUEST:
                    if not self.guest_id:
                        raise PermissionError()
                case AuthenticationRequired.USER:
                    if not self.user_id:
                        raise PermissionError()
                case AuthenticationRequired.GUEST_OR_USER:
                    if not (self.guest_id or self.user_id):
                        raise PermissionError()
                case AuthenticationRequired.GUEST_AND_USER:
                    if not (self.guest_id and self.user_id):
                        raise PermissionError()
                case _:
                    raise Exception("unknown authentication requirement")

            status = HTTPStatus.CREATED if http_dict["method"] == "POST" else HTTPStatus.OK
            body = self.handler(event=event, context=context)

        except ClientError as error:
            LOG.exception(error)
            if error.response["Error"]["Code"] == "ConditionalCheckFailedException":
                status = HTTPStatus.BAD_REQUEST
                body = {"message": "failed update condition"}
            else:
                status = HTTPStatus.INTERNAL_SERVER_ERROR
                body = {"message": error.response["Error"]["Message"]}

        except AuthException:
            LOG.error("API function requires authentication and none provided")
            status = HTTPStatus.UNAUTHORIZED
            body = {"message": "Unauthorized"}

        except PermissionError:
            LOG.error("User lacks privileges for API function")
            status = HTTPStatus.FORBIDDEN
            body = {"message": "Forbidden"}

        except KeyError as error:
            LOG.exception("key error")
            status = HTTPStatus.BAD_REQUEST
            body = {"message": str(error)}

        except CSRFException:
            LOG.error("CSRF error")
            status = PAGE_EXPIRED  # type: ignore [assignment]
            body = {"message": "CSRF error"}

        except Exception as error:
            LOG.exception("Unhandled exception")
            status = HTTPStatus.INTERNAL_SERVER_ERROR
            body = {"message": str(error)}

        csrf_token = f"{int(time() + CSRF_LIFETIME)}-{token_hex()}-"
        message = f"{csrf_token}{source_ip}".encode("ascii")
        csrf_token += hmac.new(self.secret_key, message, sha3_256).hexdigest()
        return {
            "statusCode": status,
            "headers": {"content-type": "application/json", CSRF_HEADER: csrf_token},
            "body": json.dumps(body),
        }

    @staticmethod
    def get_table(env_name: str) -> DynamoDBTable | None:
        """Get a dynamodb table"""
        name = os.getenv(env_name)
        return boto3.resource("dynamodb").Table(name) if name else None

    @classmethod
    def lambda_handler(cls) -> Callable | None:
        """A convenience method for instantiating a Lambda handler"""
        try:
            products_table = cls.get_table("PRODUCTS_TABLE")
            carts_table = cls.get_table("CARTS_TABLE")
            orders_table = cls.get_table("ORDERS_TABLE")
            env_secret = os.getenv("CSRF_SECRET_KEY")
            secret_key = env_secret.encode("ascii") if env_secret else b""
            return cls(products_table, carts_table, orders_table, secret_key).wrapper
        except:
            LOG.exception("loading object failed")
            return None

    def audit_log(self, event: AuditLogEvent, **kwargs: Any) -> None:
        """Log an event to the audit log"""
        audit_log(event, user_id=self.user_id, guest_id=self.guest_id, **kwargs)

    @staticmethod
    def get_cart_mix(cart: Cart) -> ProductMix:
        """Return what mix of items we have"""
        mix = ProductMix.NONE
        for product in cart.products:
            if product.media in ["paperback", "jewelry"]:
                mix = (
                    ProductMix.ALL_PHYSICAL
                    if mix in [ProductMix.NONE, ProductMix.ALL_PHYSICAL]
                    else ProductMix.MIX_OF_TYPES
                )
            else:
                mix = (
                    ProductMix.ALL_DIGITAL
                    if mix in [ProductMix.NONE, ProductMix.ALL_DIGITAL]
                    else ProductMix.MIX_OF_TYPES
                )
        return mix

    @staticmethod
    def get_paypal_controller() -> OrdersController:
        """Get an OrdersController from the PayPal SDK"""
        # PayPal connection is configured via environment variables so the codes won't be committed into git
        paypal_sandbox = os.getenv("PAYPAL_SANDBOX") == "True"
        paypal_client_id = os.getenv("PAYPAL_CLIENT_ID")
        paypal_client_secret = os.getenv("PAYPAL_CLIENT_SECRET")

        assert paypal_client_id
        assert paypal_client_secret

        # Configure logging
        log_config = LoggingConfiguration(
            log_level=logging.INFO if paypal_sandbox else logging.WARNING,
            mask_sensitive_headers=not paypal_sandbox,
            request_logging_config=RequestLoggingConfiguration(
                log_body=paypal_sandbox,
                log_headers=paypal_sandbox,
            ),
            response_logging_config=ResponseLoggingConfiguration(
                log_body=paypal_sandbox,
                log_headers=paypal_sandbox,
            ),
        )

        # Connect to PayPal
        paypal = PaypalServersdkClient(
            logging_configuration=log_config,
            environment=Environment.SANDBOX if paypal_sandbox else Environment.PRODUCTION,
            client_credentials_auth_credentials=ClientCredentialsAuthCredentials(
                paypal_client_id, paypal_client_secret
            ),
        )

        return paypal.orders


# TODO: put descriptions for paypal orders in db
