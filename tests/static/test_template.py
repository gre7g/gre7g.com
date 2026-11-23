"""Check if the template.json includes everything we expect

Each Lambda source file declares the AWS resources it needs in its module docstring with a line such as
"REQUIRES: CartsRW, OrdersRead" (or "REQUIRES: none"). These tests confirm that template.yaml grants each
function the environment variables, IAM policies, and timeouts those requirements imply.
"""

import logging
import re
from unittest import TestCase

from lib.local.template import Template, ROOT_PATH, Function

# Constants:
LOG = logging.getLogger(__name__)
TEMPLATE_PATH = ROOT_PATH / "template.yaml"
# Note: the requirements list could span multiple lines, so for the simplicity of parsing, keep REQUIRES at the end of
# the docstring.
SEARCH_REQUIREMENTS = re.compile(r"^REQUIRES:\s+([\w\s,]+)", re.M)
# Splits the captured REQUIRES list into individual requirement names
SEARCH_NAME = re.compile(r"\w+")
# Minimum Lambda timeouts (seconds) for functions that talk to slow external services
S3_TIMEOUT = 30
EMAIL_TIMEOUT = 30


class TestTemplate(TestCase):
    """Test template.json"""

    def setUp(self) -> None:
        """Load template.yaml and attach each function's declared REQUIRES set from its source file"""
        self.template = Template(TEMPLATE_PATH)
        for function in self.template.functions:
            with function.file_path.open("rt") as file_obj:
                source = file_obj.read()
            match = SEARCH_REQUIREMENTS.search(source)
            assert match, f"{function.name} has no requirements"
            requirements = SEARCH_NAME.findall(match.group(1))
            assert requirements, f"Found no requirements for {function.name}"
            # "REQUIRES: none" means the function needs no extra resources
            function.requirements = set([] if requirements == ["none"] else requirements)

    def test_requirements(self):
        """Function requirements must be met in configuration template"""
        for function in self.template.functions:
            # Required for each function
            function.check_env_var("JWKS_URI")
            function.check_env_var("CSRF_SECRET_KEY")

            # Requirements as listed in docstring
            for requirement in function.requirements:
                # Each requirement maps to the env vars / policies / timeouts it needs. Unrecognized names are
                # silently ignored (there is no default case).
                match requirement:
                    case "AuditRW":
                        function.check_timeout(S3_TIMEOUT)
                        function.check_env_var("AUDIT_LOG_STORAGE")
                        function.check_policy("S3CrudPolicy", "AuditLogStorage")
                    case "CartsRead":
                        function.check_env_var("CARTS_TABLE")
                        function.check_policy("DynamoDBReadPolicy", "CartsTable")
                    case "CartsRW":
                        function.check_env_var("CARTS_TABLE")
                        function.check_policy("DynamoDBCrudPolicy", "CartsTable")
                    case "OrdersRead":
                        function.check_env_var("ORDERS_TABLE")
                        function.check_policy("DynamoDBReadPolicy", "OrdersTable")
                    case "OrdersRW":
                        function.check_env_var("ORDERS_TABLE")
                        function.check_policy("DynamoDBCrudPolicy", "OrdersTable")
                    case "ProductsRead":
                        function.check_env_var("PRODUCTS_TABLE")
                        function.check_policy("DynamoDBReadPolicy", "ProductsTable")
                    case "ProductsRW":
                        function.check_env_var("PRODUCTS_TABLE")
                        function.check_policy("DynamoDBCrudPolicy", "ProductsTable")
                    case "Gmail":
                        function.check_env_var("GMAIL_APP_PASSWORD")
                        function.check_env_var("GMAIL_SERVER")
                        function.check_timeout(EMAIL_TIMEOUT)
                    case "GetUser":
                        function.check_env_var("USER_POOL")
                        function.check_policy("cognito-idp:AdminGetUser", "UserPool.Arn")
                    case _:
                        raise ValueError(f"Unknown REQUIRES: {requirement}")
