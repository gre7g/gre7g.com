"""Should produce an URL for downloading the file"""

from http import HTTPStatus
import logging

from .base_test_classes import BaseTestCase

# Constants:
LOG = logging.getLogger(__name__)


class TestDownload(BaseTestCase):
    """Should produce an URL for downloading the file"""

    def test_happy_path(self) -> None:
        """Should produce an URL for downloading the file"""
        response = self.get(
            "/api/v1/download/order1_id/product1_id",
            auth_user=self.regular_user,
        )
        assert response.status_code == HTTPStatus.OK

        from pprint import pprint

        pprint(response.json())
        1 / 0
