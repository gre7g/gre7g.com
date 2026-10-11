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

        os.environ["MYPYPATH"] = str(root_path / "todo_lib")
        for path in [
            root_path / "src",
            root_path / "todo_lib",
        ]:
            check_call(["mypy", str(path)])
