"""Check if there are any known vulnerabilities in the installed packages"""

from subprocess import check_call
from unittest import TestCase


class TestPipAudit(TestCase):
    """Check if there are any known vulnerabilities in the installed packages"""

    def test_pip_audit(self):
        """Check if there are any known vulnerabilities in the installed packages"""

        check_call(["pip-audit"])
