"""
Test miscellaneous checks on the lambda functions

Covers the cross-cutting behavior in LambdaBase: routing of unsupported methods, authentication, and CSRF protection.
CSRF tokens have the form "<expiry>-<random hex>-<HMAC-SHA3-256 of the first two parts plus the client IP>".
"""

from hashlib import sha3_256
import hmac
from http import HTTPStatus
import logging
import os
from secrets import token_hex
from time import time

from .base_test_classes import BaseTestCase
from lambda_base import CSRF_HEADER, PAGE_EXPIRED
from lib.local.integration_base import Validate, SKIP_LOCAL, NO_CLOUD

# Constants:
LOG = logging.getLogger(__name__)


class TestMisc(BaseTestCase):
    """Test miscellaneous checks on the lambda functions"""

    def test_bad_method(self):
        """Should reject access with a bad method"""
        # Seed some orders so that order paths exist and a 404 can't simply be blamed on a missing record
        orders, order_dict = self.order_data()
        with self.create_records([(self.orders_table, orders[0]), (self.orders_table, orders[1])]):
            for path, methods in [
                ("/api/v1/cart", ["DELETE"]),
                ("/api/v1/cart/shipping", ["GET", "PUT", "DELETE"]),
                ("/api/v1/click_id", ["GET", "PUT", "DELETE"]),
                ("/api/v1/guest", ["GET", "DELETE"]),
                ("/api/v1/order", ["PUT", "DELETE"]),
                ("/api/v1/order/order1_id", ["POST", "DELETE"]),
                ("/api/v1/products", ["POST", "PUT", "DELETE"]),
            ]:
                # Skip validation since the OpenAPI spec doesn't define these method/path combinations
                for method in methods:
                    response = self.request(
                        method,
                        path,
                        auth_user=self.regular_user,
                        validate=Validate.NOTHING,
                    )
                    assert response.status_code == HTTPStatus.NOT_FOUND, f"Unexpected response to {method} {path}"

    # The local simulation bypasses JWT verification, so this is only meaningful against real Cognito tokens
    @SKIP_LOCAL
    def test_bad_auth(self):
        """Should reject access with a bad authentication"""
        response = self.get(
            "/api/v1/order",
            headers={"authorization": "bearer one.two.three"},
            validate=Validate.NOTHING,
        )
        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_csrf(self):
        """Should reject writes with an invalid CSRF token"""
        # Validate.CSRF_ONLY stops request() from sending the cached token and from retrying on PAGE_EXPIRED, so each
        # call below sees the server's first verdict
        # No token required for GETs
        response = self.get(
            "/api/v1/cart",
            validate=Validate.CSRF_ONLY,
        )
        assert response.status_code != PAGE_EXPIRED

        # Token required for POST/PUT/DELETE
        response = self.post(
            "/api/v1/guest",
            validate=Validate.CSRF_ONLY,
        )
        assert response.status_code == PAGE_EXPIRED

        # Bad token: well-formed and unexpired, but the signature is garbage
        csrf_token = f"{int(time())+60}-123456-123456"
        response = self.post(
            "/api/v1/guest",
            headers={"Content-Type": "application/json", CSRF_HEADER: csrf_token},
            validate=Validate.CSRF_ONLY,
        )
        assert response.status_code == PAGE_EXPIRED

    # Test locally, we're not coordinating clocks in the cloud.
    @NO_CLOUD
    def test_expired_csrf(self):
        """Should reject writes with an expired CSRF token"""
        # Forge tokens with the shared secret, which is only available locally. The simulation reports every request as
        # coming from 1.2.3.4, so that IP is part of the signed message.
        secret_key = os.getenv("CSRF_SECRET_KEY")
        assert secret_key

        # Still good
        csrf_token = f"{int(time() + 60)}-{token_hex()}-"
        message = f"{csrf_token}1.2.3.4".encode("ascii")
        csrf_token += hmac.new(secret_key.encode("ascii"), message, sha3_256).hexdigest()
        response = self.post(
            "/api/v1/guest",
            headers={"Content-Type": "application/json", CSRF_HEADER: csrf_token},
            validate=Validate.CSRF_ONLY,
        )
        assert response.status_code != PAGE_EXPIRED

        # Expired 1s ago
        csrf_token = f"{int(time() - 1)}-{token_hex()}-"
        message = f"{csrf_token}1.2.3.4".encode("ascii")
        csrf_token += hmac.new(secret_key.encode("ascii"), message, sha3_256).hexdigest()
        response = self.post(
            "/api/v1/guest",
            headers={"Content-Type": "application/json", CSRF_HEADER: csrf_token},
            validate=Validate.CSRF_ONLY,
        )
        assert response.status_code == PAGE_EXPIRED

    # Test locally, we're not dealing with real IP addresses.
    @NO_CLOUD
    def test_stolen_csrf(self):
        """Should reject writes with an CSRF token taken from another machine"""
        # Both tokens are unexpired and correctly signed; only the IP baked into the signature differs
        secret_key = os.getenv("CSRF_SECRET_KEY")
        assert secret_key

        # From our (simulated) IP
        csrf_token = f"{int(time() + 60)}-{token_hex()}-"
        message = f"{csrf_token}1.2.3.4".encode("ascii")
        csrf_token += hmac.new(secret_key.encode("ascii"), message, sha3_256).hexdigest()
        response = self.post(
            "/api/v1/guest",
            headers={"Content-Type": "application/json", CSRF_HEADER: csrf_token},
            validate=Validate.CSRF_ONLY,
        )
        assert response.status_code != PAGE_EXPIRED

        # From another IP
        csrf_token = f"{int(time() + 60)}-{token_hex()}-"
        message = f"{csrf_token}99.99.99.99".encode("ascii")
        csrf_token += hmac.new(secret_key.encode("ascii"), message, sha3_256).hexdigest()
        response = self.post(
            "/api/v1/guest",
            headers={"Content-Type": "application/json", CSRF_HEADER: csrf_token},
            validate=Validate.CSRF_ONLY,
        )
        assert response.status_code == PAGE_EXPIRED
