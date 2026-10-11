"""Utilities for managing an audit log"""

from dataclasses import dataclass
from hashlib import sha224
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


@dataclass
class AuditPath:
    path: Path
    wildcard: str | None = "*.py"
    recursive: bool = True


# Constants:
AUDIT_LOG = logging.getLogger(__name__)
ROOT_PATH = Path(__file__).parents[1]
LOG_PATH = ROOT_PATH / "audit_log" / "audit.log"
AUDIT_PATHS = [
    AuditPath(ROOT_PATH / "index.html", None, False),
    AuditPath(ROOT_PATH / "src/api"),
    AuditPath(ROOT_PATH / "src/typescripts", "*.ts"),
    AuditPath(ROOT_PATH / "todo_lib"),
    AuditPath(ROOT_PATH / "static", "*"),
    AuditPath(ROOT_PATH / "api.yaml", None, False),
    AuditPath(ROOT_PATH / "template.yaml", None, False),
]
DEPLOY_PATH = ROOT_PATH / "audit_log" / "deployments.p"


class SourceHash:
    """A class for calculating a hash across all the source files"""

    @staticmethod
    def _sortable_filename(path: Path) -> str:
        """Convert a source path into a sortable string"""
        strings: list[str] = []
        while path != ROOT_PATH:
            strings.insert(0, path.name)
            path = path.parent
        return "/".join(strings)

    def _get_file_map(self) -> dict[str, Path]:
        """Get a dictionary that maps sortable filenames to source paths"""
        files: dict[str, Path] = {}
        for audit_path in AUDIT_PATHS:
            if audit_path.wildcard is None:
                files[self._sortable_filename(audit_path.path)] = audit_path.path
            else:
                for path in audit_path.path.glob(audit_path.wildcard):
                    files[self._sortable_filename(path)] = path
        return files

    def get_hash(self) -> str:
        """Get the hash of all the source files"""
        # Get a list of the source files
        file_map = self._get_file_map()
        file_list = list(file_map)
        file_list.sort()

        # Hash the file list
        bin_file_list = ("\n".join(file_list)).encode()
        hash_obj = sha224(bin_file_list)

        # Hash the file contents
        for filename in file_list:
            path = file_map[filename]
            with open(path, "rb") as file_obj:
                hash_obj.update(file_obj.read())

        hash_str = hash_obj.hexdigest()
        AUDIT_LOG.info("Source hash: %s", hash_str)
        return hash_str


def configure_audit_log(show_audit_log: bool) -> None:
    """Enable the audit log"""
    AUDIT_LOG.setLevel(logging.INFO)
    AUDIT_LOG.propagate = show_audit_log
    handler = RotatingFileHandler(LOG_PATH, maxBytes=20000, backupCount=5)
    handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
    AUDIT_LOG.addHandler(handler)
