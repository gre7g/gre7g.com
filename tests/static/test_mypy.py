"""Check static analysis on source code"""

import os
from pathlib import Path
from subprocess import check_call
from unittest import TestCase


class TestMypy(TestCase):
    """Check static analysis on source code"""

    def test_mypy(self):
        """Check static analysis on source code"""

        root_path = Path(__file__).resolve().parents[2]
        os.chdir(str(root_path))

        check_call(["mypy", str(root_path / "src"), str(root_path / "gre7g_lib")])
