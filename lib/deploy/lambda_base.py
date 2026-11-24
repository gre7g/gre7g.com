"""Various utilities used in lambdas and testing

Each API lambda subclasses "LambdaBase", implements "handler()", and exposes "Subclass.lambda_handler()" at
module level. That instance is created once per container and reused across warm invocations, so per-request state
held on "self" must be reset at the start of each call.
"""

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
from threading import Thread
from time import time
from types_boto3_dynamodb.service_resource import Table as DynamoDBTable
from typing import Any, Callable

from audit_log import AuditLogEvent, audit_log
from database import UserId, Cart, Order, Product

# Constants:
# Use the Powertools structured logger when running inside Lambda, plain stdlib logging otherwise (tests, local runs).
LOG = Logger(__name__) if os.getenv("AWS_LAMBDA_FUNCTION_NAME") else logging.getLogger(__name__)
# Only asymmetric algorithms are accepted. Allowing HS* would let an attacker sign tokens using the public key as an
# HMAC secret.
SIGN_ALGORITHMS = ["RS256", "RS384", "RS512", "ES256", "ES384", "ES512"]
CSRF_LIFETIME = 300  # 5 minutes
CSRF_HEADER = "x-csrf-token"  # Lowercase because API Gateway HTTP APIs deliver header names lowercased
PAGE_EXPIRED = 419  # Non-standard "Page Expired" status (popularized by Laravel); not in HTTPStatus
PHYSICAL_SHIPPING = 5.99  # $5.99 for shipping paperbacks and jewelry in the US
CURRENCY = "USD"
DOWNLOAD_WINDOW = 3600  # 1 hour authentication to download the files
GLACIER_LAKE_BUCKET = "gre7g-com-downloads"  # S3 bucket holding purchasable download files


class AuthException(Exception):
    """Authentication required (mapped to 401 Unauthorized; raised by handlers, not by the base class)"""


class CSRFException(Exception):
    """CSRF expired or could not be authenticated (mapped to the 419 PAGE_EXPIRED status)"""


class AuthenticationRequired(StrEnum):
    """Authentication required at the lambda level

    Set as the "AUTH_REQUIRED" class attribute on a "LambdaBase" subclass. A failed check raises
    "PermissionError", which is returned as 403 Forbidden.
    """

    # Basic rights
    NONE = auto()  # Anyone may call
    GUEST = auto()  # Requires an x-guest-id header
    USER = auto()  # Requires a valid Cognito bearer token
    GUEST_OR_USER = auto()  # Requires either identity
    GUEST_AND_USER = auto()  # Requires both, e.g. to merge a guest cart into a user's cart at login


class ProductMix(StrEnum):
    """Describes a mix of products (physical vs. digital), used to decide on shipping and login requirements"""

    NONE = auto()
    ALL_DIGITAL = auto()
    ALL_PHYSICAL = auto()
    MIX_OF_TYPES = auto()


@dataclass
class LambdaBase(ABC):
    """Base class for lambdas

    Subclasses implement "handler()" and may set "AUTH_REQUIRED". Calling the instance ("__call__") parses the
    request, authenticates it, runs the handler, maps exceptions to HTTP responses, and issues a fresh CSRF token.
    """

    # Long-lived resources, set once by lambda_handler() at cold start (None if the env var is unset)
    products_table: DynamoDBTable | None = None
    carts_table: DynamoDBTable | None = None
    orders_table: DynamoDBTable | None = None
    secret_key: bytes = b""  # HMAC key for signing CSRF tokens

    # Per-request state, populated by __call__ before handler() runs
    path_parameters: dict = field(default_factory=dict)
    user_id: UserId | None = None  # Cognito "sub" of a logged-in user
    guest_id: UserId | None = None  # Client-supplied x-guest-id header (unauthenticated)
    body: dict[str, Any] = field(default_factory=dict)

    # Background audit-log uploads; joined before the response is returned
    threads: list[Thread] = field(default_factory=list)

    AUTH_REQUIRED = AuthenticationRequired.NONE

    @abstractmethod
    def handler(self, event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
        """Overload this function with your handler code

        Returns:
            The JSON-serializable response body. The status code is chosen by "__call__" (201 for POST, else 200)
            unless an exception is raised.
        """
        raise NotImplementedError  # pragma: no cover

    def extract_user_id(self, event: dict[str, Any]) -> None:
        """Set "self.user_id" from the JWT bearer token's "sub" claim, if present and valid

        The token's signature is verified against the issuer's JWKS ("JWKS_URI"), as are its expiry and issuer
        ("JWT_ISSUER"). The audience is not checked. Any failure is logged and leaves "user_id" as None, so an
        invalid token is treated the same as no token; "AUTH_REQUIRED" then decides whether that is acceptable.
        """
        self.user_id = None
        auth_header = (event.get("headers") or {}).get("authorization", "")
        try:
            # Note: the scheme match is case-sensitive; the frontend (api.ts) sends lowercase "bearer", but a standard
            # "Bearer <token>" header would be silently ignored.
            if auth_header.startswith("bearer "):
                token = auth_header[7:]
                uri = os.environ.get("JWKS_URI")
                assert uri
                # Fetches the key set over HTTP and picks the key matching the token's "kid" header.
                jwks_client = jwt.PyJWKClient(uri)
                signing_key = jwks_client.get_signing_key_from_jwt(token)
                # Audience verification is disabled; Cognito access tokens carry "client_id" rather than "aud".
                claims = jwt.decode(
                    token,
                    signing_key.key,
                    algorithms=SIGN_ALGORITHMS,
                    issuer=os.environ.get("JWT_ISSUER"),
                    options={"verify_aud": False},
                )
                self.user_id = UserId(claims["sub"])
        except:  # pragma: no cover
            # Tested in cloud only
            LOG.exception("failed to authenticate bearer token")

    def validate_csrf(self, csrf_header: str, source_ip: str) -> None:
        """Validate CSRF token

        Tokens have the form "<expiry>-<random hex>-<signature>", where the signature is an HMAC-SHA3-256 over
        "<expiry>-<random hex>-<source ip>" keyed with "secret_key". This makes the scheme stateless (nothing is
        stored server-side) and binds each token to the client IP it was issued to. Tokens are not single-use; any
        valid token may be replayed from the same IP until it expires.

        Args:
            csrf_header: The value of the x-csrf-token header (empty string if absent).
            source_ip: The client's IP address as reported by API Gateway.

        Raises:
            CSRFException: If the token is missing, expired, or has a bad signature.
            ValueError: If the token is malformed (not three dash-separated parts, or a non-numeric expiry).
        """
        if csrf_header:
            expiry, random_bits, signature = csrf_header.split("-")
            # We use time() and not monotonic() because the token could be generated on one machine and validated on
            # another.
            if float(expiry) >= time():
                # Recompute the expected token from its own expiry/random parts and compare in constant time to avoid
                # leaking the signature through timing.
                csrf_token = f"{expiry}-{random_bits}-"
                message = f"{csrf_token}{source_ip}".encode("ascii")
                csrf_token += hmac.new(self.secret_key, message, sha3_256).hexdigest()
                if hmac.compare_digest(csrf_header, csrf_token):
                    return
        raise CSRFException()

    def __call__(self, event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
        """Wrapper around the handler that takes care of parameters, privileges, and error handling

        This is the actual Lambda entry point. It expects an API Gateway HTTP API (payload format 2.0) event.

        Args:
            event: The API Gateway event.
            context: The Lambda context, passed through to "handler()".

        Returns:
            An API Gateway response dict with a JSON body and a newly issued CSRF token header. Every response,
            including errors, carries a fresh token so the client can always make its next request.
        """
        # Read outside the try block: these are needed to build the response, even for failed requests.
        http_dict = event["requestContext"]["http"]
        source_ip = http_dict["sourceIp"]
        try:
            self.path_parameters = event.get("pathParameters") or {}
            self.extract_user_id(event)
            headers = event.get("headers") or {}
            # The guest ID is an unauthenticated, client-chosen identifier; treat it as a cart handle, not proof of
            # identity.
            self.guest_id = headers.get("x-guest-id")
            self.body = json.loads(event["body"]) if event.get("body") else {}
            # GET requests are assumed side-effect free, so only state-changing methods need a CSRF token. This also
            # lets the client fetch its first token with a GET.
            if http_dict["method"] != "GET":
                self.validate_csrf(headers.get(CSRF_HEADER, ""), source_ip)

            match self.AUTH_REQUIRED:
                case AuthenticationRequired.NONE:
                    pass
                case AuthenticationRequired.GUEST:  # pragma: no cover
                    # Don't know that I'll ever use this
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
                case _:  # pragma: no cover
                    raise Exception("unknown authentication requirement")

            status = HTTPStatus.CREATED if http_dict["method"] == "POST" else HTTPStatus.OK
            body = self.handler(event=event, context=context)

        # Map exceptions to HTTP responses (the catch-all Exception handler must stay last).
        except ClientError as error:
            LOG.exception(str(error))
            # A failed DynamoDB ConditionExpression means the request conflicted with the current data (e.g. a stale
            # update), so it's reported as a client error rather than a server fault.
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

        # Usually a missing field in the request body or path, or a get_item() that found no row
        except KeyError as error:
            LOG.exception("key error")
            status = HTTPStatus.BAD_REQUEST
            body = {"message": str(error)}

        except CSRFException:
            LOG.error("CSRF error")
            status = PAGE_EXPIRED  # type: ignore [assignment]
            body = {"message": "CSRF error"}

        except Exception as error:  # pragma: no cover
            LOG.exception("Unhandled exception")
            status = HTTPStatus.INTERNAL_SERVER_ERROR
            body = {"message": str(error)}

        # Wait for background audit-log uploads; once we return, Lambda may freeze the process mid-request.
        for thread in self.threads:
            thread.join()
        self.threads = []

        # Issue a fresh token (same format as checked in validate_csrf) for the client's next request.
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
        """Get a dynamodb table whose name is in the given environment variable (None if the variable is unset)"""
        name = os.getenv(env_name)
        return boto3.resource("dynamodb").Table(name) if name else None

    @classmethod
    def lambda_handler(cls) -> Callable | None:
        """A convenience method for instantiating a Lambda handler

        Intended to be called once at module import ("lambda_handler = MyLambda.lambda_handler()"), so table
        resources and the CSRF key are set up at cold start and reused across warm invocations.

        Returns:
            The handler instance (callable as "handler(event, context)"), or None if construction failed. A None
            handler makes every invocation fail, but the cause is logged here at cold start.
        """
        try:
            products_table = cls.get_table("PRODUCTS_TABLE")
            carts_table = cls.get_table("CARTS_TABLE")
            orders_table = cls.get_table("ORDERS_TABLE")
            env_secret = os.getenv("CSRF_SECRET_KEY")
            secret_key = env_secret.encode("ascii") if env_secret else b""
            return cls(products_table, carts_table, orders_table, secret_key)
        except:  # pragma: no cover
            LOG.exception("loading object failed")
            return None

    def audit_log(self, event: AuditLogEvent, **kwargs: Any) -> None:
        """Log an event to the audit log, tagged with the current user and guest IDs

        The upload runs in the background and is joined at the end of "__call__".
        """
        self.threads.append(audit_log(event, user_id=self.user_id, guest_id=self.guest_id, **kwargs))

    @staticmethod
    def physical_item(media: str) -> bool:
        """Return True if the media type is a physical item"""
        return media in ["paperback", "jewelry"]

    def get_product_mix(self, products: list[Product]) -> ProductMix:
        """Return what mix of items we have

        Starts at NONE and moves to ALL_PHYSICAL/ALL_DIGITAL on the first product, then to MIX_OF_TYPES (which is
        sticky) as soon as a product of the other kind appears.
        """
        mix = ProductMix.NONE
        for product in products:
            if self.physical_item(product.media):
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
        """Get an OrdersController from the PayPal SDK

        Uses the sandbox when "PAYPAL_SANDBOX" is exactly "True"; otherwise production. In the sandbox, request and
        response bodies/headers are logged verbosely for debugging; in production logging is minimal and sensitive
        headers are masked.

        Raises:
            AssertionError: If "PAYPAL_CLIENT_ID" or "PAYPAL_CLIENT_SECRET" is not set.
        """
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

    @staticmethod
    def sign_downloads(order: Order) -> None:
        """Attach signed URLs to an order

        Replaces each product's download entry (keyed by S3 key) in place with a presigned GET URL valid for
        "DOWNLOAD_WINDOW" seconds. Generating the URL is a local signing operation; no S3 request is made, and the
        object's existence is not checked. The order should not be saved back to the table afterward!
        """
        for product in order.products:
            for filename in product.downloads:
                product.downloads[filename] = boto3.client("s3").generate_presigned_url(
                    "get_object",
                    Params={"Bucket": GLACIER_LAKE_BUCKET, "Key": filename},
                    ExpiresIn=DOWNLOAD_WINDOW,
                )

    def get_email_by_sub(self) -> str | None:
        """Look up the logged-in user's e-mail address in the Cognito user pool ("USER_POOL")

        Uses the admin API with the user's "sub" as the username, which works for pools where the sub is accepted as
        an alias for the username. Requires the lambda to have cognito-idp:AdminGetUser permission.

        Returns:
            The "email" attribute, or None if it is missing or the lookup fails (failures are logged, not raised).
        """
        try:
            response = boto3.client("cognito-idp").admin_get_user(
                UserPoolId=os.getenv("USER_POOL"), Username=self.user_id
            )

            for attr in response.get("UserAttributes", []):
                if attr["Name"] == "email":
                    return attr["Value"]
        except:  # pragma: no cover
            LOG.exception("Unable to fetch email")

        return None  # pragma: no cover
