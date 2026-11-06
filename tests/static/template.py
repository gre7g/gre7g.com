"""Check if the template.json includes everything we expect"""

import logging
import re
from unittest import TestCase

from lib.local.template import Template, ROOT_PATH, Function

# Constants:
LOG = logging.getLogger(__name__)
TEMPLATE_PATH = ROOT_PATH / "template.yaml"
SEARCH_REQUIREMENTS = re.compile(r"^REQUIRES:\s+([\w\s,]+)", re.M)
SEARCH_NAME = re.compile(r"\w+")
S3_TIMEOUT = 30


class TestTemplate(TestCase):
    """Test template.json"""

    def setUp(self) -> None:
        self.template = Template(TEMPLATE_PATH)
        for function in self.template.functions:
            with function.file_path.open("rt") as file_obj:
                source = file_obj.read()
            match = SEARCH_REQUIREMENTS.search(source)
            assert match, f"{function.name} has no requirements"
            requirements = SEARCH_NAME.findall(match.group(1))
            assert requirements, f"Found no requirements for {function.name}"
            function.requirements = set([] if requirements == ["none"] else requirements)

    @staticmethod
    def check_timeout(function: Function, timeout: int):
        assert (function.timeout or 0) >= timeout, f"{function.name} must have a timeout of {timeout}"

    @staticmethod
    def check_env_var(function: Function, var_name: str):
        assert var_name in function.env_vars, f"{function.name} must have access to {var_name}"

    @staticmethod
    def check_policy(function: Function, policy_name: str, resource_name: str):
        assert (
            policy_name,
            resource_name,
        ) in function.policies, f"{function.name} must have {policy_name} on {resource_name}"

    def test_requirements(self):
        """Function requirements must be met in configuration template"""
        for function in self.template.functions:
            for requirement in function.requirements:
                match requirement:
                    case "AuditRW":
                        self.check_timeout(function, S3_TIMEOUT)
                        self.check_env_var(function, "AUDIT_LOG_STORAGE")
                        self.check_policy(function, "S3CrudPolicy", "AuditLogStorage")
                    case "CartsRead":
                        self.check_env_var(function, "CARTS_TABLE")
                        self.check_policy(function, "DynamoDBReadPolicy", "CartsTable")
                    case "CartsRW":
                        self.check_env_var(function, "CARTS_TABLE")
                        self.check_policy(function, "DynamoDBCrudPolicy", "CartsTable")
                    case "OrdersRead":
                        self.check_env_var(function, "ORDERS_TABLE")
                        self.check_policy(function, "DynamoDBReadPolicy", "OrdersTable")
                    case "OrdersRW":
                        self.check_env_var(function, "ORDERS_TABLE")
                        self.check_policy(function, "DynamoDBCrudPolicy", "OrdersTable")
                    case "ProductsRead":
                        self.check_env_var(function, "PRODUCTS_TABLE")
                        self.check_policy(function, "DynamoDBReadPolicy", "ProductsTable")
                    case "ProductsRW":
                        self.check_env_var(function, "PRODUCTS_TABLE")
                        self.check_policy(function, "DynamoDBCrudPolicy", "ProductsTable")
