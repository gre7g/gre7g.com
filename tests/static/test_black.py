"""Check if all source files have been properly formatted"""

import os
from pathlib import Path
from subprocess import check_call
import sys
from unittest import TestCase


class TestBlack(TestCase):
    """Check if all source files have been properly formatted"""

    def test_code_is_blackened(self):
        """Check if all source files have been properly formatted"""

        root_path = Path(__file__).resolve().parents[2]
        os.chdir(str(root_path))

        for path in [
            root_path / "scripts",
            root_path / "src",
            root_path / "tests",
            root_path / "todo_lib",
        ]:
            check_call([sys.executable, "-m", "black", "--check", str(path)])
