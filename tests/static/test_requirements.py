"""Check for errors in the requirements files"""

import logging
from pathlib import Path
from pip_requirements_parser import RequirementsFile
from shutil import which
from subprocess import check_output
from unittest import TestCase

# Constants:
LOG = logging.getLogger(__name__)
ROOT_PATH = Path(__file__).parents[2]
ROOT_REQUIREMENTS = ROOT_PATH / "requirements.txt"
SRC_API_REQUIREMENTS = ROOT_PATH / "src" / "api" / "requirements.txt"
LIB_REQUIREMENTS = ROOT_PATH / "gre7g_lib" / "requirements.txt"
TEST_REQUIREMENTS = ROOT_PATH / "tests" / "requirements.txt"
DEV_REQUIREMENTS = ROOT_PATH / "dev-requirements.txt"


class TestRequirements(TestCase):
    """Check for errors in the requirements files"""

    def requirement_path(self, path: Path) -> dict[str, list[str]]:
        return self.requirement_obj(RequirementsFile.from_file(str(path)))

    @staticmethod
    def requirement_obj(requirements_obj: RequirementsFile) -> dict[str, list[str]]:
        assert not requirements_obj.invalid_lines
        requirements_dict = {}
        for requirement in requirements_obj.requirements:
            requirement_dict = requirement.to_dict()
            requirements_dict[requirement_dict["name"]] = requirement_dict["specifier"]
        return requirements_dict

    def test_requirements(self):
        """Check for errors in the requirements files"""
        pip_requirements = self.requirement_obj(
            RequirementsFile.from_string(check_output([which("pip"), "freeze"], text=True))
        )
        root_requirements = self.requirement_path(ROOT_REQUIREMENTS)
        src_api_requirements = self.requirement_path(SRC_API_REQUIREMENTS)
        lib_requirements = self.requirement_path(LIB_REQUIREMENTS)
        test_requirements = self.requirement_path(TEST_REQUIREMENTS)
        dev_requirements = self.requirement_path(DEV_REQUIREMENTS)

        file_dict = {
            str(ROOT_REQUIREMENTS): root_requirements,
            str(SRC_API_REQUIREMENTS): src_api_requirements,
            str(LIB_REQUIREMENTS): lib_requirements,
            str(TEST_REQUIREMENTS): test_requirements,
        }

        # All requirements should be installed
        for filename, requirements in file_dict.items():
            for package, versions in requirements.items():
                assert package in pip_requirements, f"cannot find {package} listed in {filename}"
                assert pip_requirements[package] == versions

        # Root, source, and lib requirements should be the same
        assert root_requirements == src_api_requirements
        assert root_requirements == lib_requirements

        # Root requirements should be a subset of dev and test requirements
        for package, versions in root_requirements.items():
            assert (
                dev_requirements.get(package) == versions
            ), f"root requirement {package} does not match dev requirement"
            assert (
                test_requirements.get(package) == versions
            ), f"root requirement {package} does not match test requirement"
