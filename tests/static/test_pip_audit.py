"""Check if there are any known vulnerabilities in the installed packages"""

from subprocess import check_call
from unittest import TestCase


class TestPipAudit(TestCase):
    """Check if there are any known vulnerabilities in the installed packages"""

    def test_pip_audit(self):
        """Check if there are any known vulnerabilities in the installed packages"""

        # Audits the currently active environment; a non-zero exit (vulnerability found) fails the test
        check_call(["pip-audit"])
