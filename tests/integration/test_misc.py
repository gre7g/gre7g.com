"""Test miscellaneous checks on the lambda functions"""

from hashlib import sha3_256
import hmac
from http import HTTPStatus
import logging
import os
from secrets import token_hex
from time import time

from gre7g_utils import CSRF_HEADER, PAGE_EXPIRED
from integration_base import BaseTestCase, Validate, SKIP_LOCAL, NO_CLOUD

# Constants:
LOG = logging.getLogger(__name__)


class TestMisc(BaseTestCase):
    """Test miscellaneous checks on the lambda functions"""

    def test_bad_method(self):
        """Should reject access with a bad method"""
        for path, methods in [
            ("/api/v1/cart", ["DELETE"]),
            ("/api/v1/click_id", ["GET", "PUT", "DELETE"]),
            ("/api/v1/download/order1_id", ["POST", "PUT", "DELETE"]),
            ("/api/v1/guest", ["GET", "DELETE"]),
            ("/api/v1/order", ["POST", "PUT", "DELETE"]),
            ("/api/v1/products", ["POST", "PUT", "DELETE"]),
        ]:
            for method in methods:
                response = self.request(
                    method,
                    path,
                    auth_user=self.regular_user,
                    validate=Validate.NOTHING,
                )
                assert response.status_code == HTTPStatus.NOT_FOUND

    @SKIP_LOCAL
    def test_bad_auth(self):
        """Should reject access with a bad authentication"""
        response = self.get(
            "/api/v1/download/order1_id",
            headers={"Authorization": "Bearer one.two.three"},
            validate=Validate.NOTHING,
        )
        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_csrf(self):
        """Should reject writes with an invalid CSRF token"""
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

        # Bad token
        csrf_token = f"{int(time())+60}-123456-123456"
        response = self.post(
            "/api/v1/guest",
            headers={"Content-Type": "application/json", CSRF_HEADER: csrf_token},
            validate=Validate.CSRF_ONLY,
        )
        assert response.status_code == PAGE_EXPIRED

    @NO_CLOUD
    def test_expired_csrf(self):
        """Should reject writes with an expired CSRF token"""
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

    @NO_CLOUD
    def test_stolen_csrf(self):
        """Should reject writes with an CSRF token taken from another machine"""
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
