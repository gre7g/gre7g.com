"""A "hack" that replaces boto3 with a mock library for local testing"""

import boto3
from botocore.exceptions import ClientError
from dataclasses import dataclass, field
from decimal import Decimal
from http import HTTPStatus
from http.server import HTTPServer, BaseHTTPRequestHandler
from importlib import import_module
import jwt
import logging
import os
from pathlib import Path
import re
from time import sleep
from threading import Thread
from typing import NewType, ClassVar, Any
from unittest.mock import Mock
from urllib.parse import urlencode, urlsplit
import yaml

# Types:
EnvVar = NewType("EnvVar", str)
TableName = NewType("TableName", str)
PolicyName = NewType("PolicyName", str)
UserId = NewType("UserId", str)
GroupId = NewType("GroupId", str)
Policies = list[tuple[PolicyName, TableName]]

# Constants:
LOG = logging.getLogger(__name__)
SUB_REF = re.compile(r"!(Ref|Sub|GetAtt|If|Equals)\b")
PARAMETERS = re.compile(r"\{(\w+)}")
RW_POLICY = "DynamoDBCrudPolicy"
RO_POLICY = "DynamoDBReadPolicy"
DELAY_SERVER_START = 0.2


def hack_jwt_decode(token, key, algorithms, issuer, options) -> dict[str, str]:
    """Bypasses JWT verification and decoding"""
    return {"sub": token}


class RequestHandler(BaseHTTPRequestHandler):
    """Handles requests from the local webserver"""

    def call_func(self, method: str):
        """Handle a generic request"""
        content = self.rfile.read(int(self.headers["Content-Length"] or 0))
        parsed = urlsplit(self.path)
        response = boto3.resource.call_func(parsed.path, method, self.headers, content, parsed.query)
        self.send_response(response["statusCode"], response.get("message"))
        for key, value in response["headers"].items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(response["body"].encode())

    def do_GET(self):
        """Handle a GET request"""
        self.call_func("get")

    def do_POST(self):
        """Handle a POST request"""
        self.call_func("post")

    def do_DELETE(self):
        """Handle a DELETE request"""
        self.call_func("delete")

    def do_PUT(self):
        """Handle a PUT request"""
        self.call_func("put")


@dataclass
class Table:
    """A mocked out dynamodb table"""

    keys: list[str] = field(default_factory=list)
    records: dict = field(default_factory=dict)
    policy: str = ""

    SECRET_OVERRIDE: ClassVar[bool] = False

    def _key(self, key_dict: dict) -> tuple:
        """Represent a key as a tuple"""
        return tuple([key_dict[key] for key in self.keys])

    @staticmethod
    def decimalize(data: dict) -> dict:
        """Convert any numerical values to Decimal"""
        return {key: Decimal(value) if type(value) in [int, float] else value for key, value in data.items()}

    def get_item(self, Key: dict) -> dict:
        """Get a table row"""
        if (self.policy not in (RO_POLICY, RW_POLICY)) and not self.SECRET_OVERRIDE:
            raise ClientError({"Error": {"Code": "AccessDeniedException", "Message": "Permission Denied"}}, "get_item")
        key = self._key(Key)
        return {"Item": self.records[key]} if key in self.records else {}

    def delete_item(self, Key: dict):
        """Delete a table row"""
        if (self.policy != RW_POLICY) and not self.SECRET_OVERRIDE:
            raise ClientError(
                {"Error": {"Code": "AccessDeniedException", "Message": "Permission Denied"}}, "delete_item"
            )
        key = self._key(Key)
        if key in self.records:
            del self.records[key]

    def put_item(self, Item: dict) -> None:
        """Write a table row"""
        if (self.policy != RW_POLICY) and not self.SECRET_OVERRIDE:
            raise ClientError({"Error": {"Code": "AccessDeniedException", "Message": "Permission Denied"}}, "put_item")
        self.records[self._key(Item)] = Item

    def query(self, KeyConditionExpression):
        """Query a database"""
        # Not sure it's worth the hassle to try and implement this, so let's just return everything
        return {"Items": list(self.records.values())}

    def scan(self):
        """Scan all records in a database"""
        return {"Items": list(self.records.values())}


@dataclass
class Function:
    """Represents a lambda function in the `template.yaml` file"""

    code_uri: str
    handler: str
    path: re.Pattern[str]
    method: str
    policies: Policies = field(default_factory=Policies)
    env_vars: dict[EnvVar, TableName] = field(default_factory=dict)

    def __call__(self, event, context) -> dict:
        """Call the lambda function"""
        path = f"{self.code_uri.replace("/", ".")}.{self.handler}".split(".")
        module = path[:-1]
        function = path[-1]
        return getattr(import_module(".".join(module)), function)(event, context)


@dataclass
class HackBoto:
    """Hacked replacement for boto3"""

    template: Path
    users: dict[UserId, list[GroupId]] = field(default_factory=dict)
    tables: dict[TableName, Table] = field(default_factory=dict)
    functions: list[Function] = field(default_factory=list)
    s3_objects: dict[str, str] = field(default_factory=dict)

    @staticmethod
    def compile_path(path: str) -> re.Pattern[str]:
        """Generates a regular expression pattern for fetching parameters out of an URL path"""
        pattern = PARAMETERS.sub(r"(?P<\1>[\\w-]+)", path)
        return re.compile(f"^{pattern}$")

    def apply_hack(self):
        """Apply the hack so boto3 runs locally instead of contacting the cloud"""
        # Read template file
        with self.template.open("rt") as file_obj:
            template_str = file_obj.read()

        # The yaml library doesn't deal well with !Ref, !Sub, !GetAtt, !If, and !Equals, but that's okay. We don't need
        # them, so just strip them out.
        template = yaml.load(SUB_REF.sub("", template_str), yaml.Loader)

        # Loop over the resources and find the tables and serverless functions
        for key, value in template["Resources"].items():
            properties = value.get("Properties", {})
            match value["Type"]:
                case "AWS::DynamoDB::Table":
                    # Find the table keys
                    keys = [attribute["AttributeName"] for attribute in properties.get("KeySchema", [])]

                    # Create the table
                    self.tables[key] = Table(keys)

                case "AWS::Serverless::Function":
                    # Find policies
                    policies = Policies()
                    for item in properties.get("Policies", []):
                        policy = next(iter(item))
                        if "TableName" in item[policy]:  # Not all policies are for dynamodb tables
                            policies.append((PolicyName(policy), TableName(item[policy]["TableName"])))

                    # Find environment variables
                    # Mildly amusing sidenote: This sets the secret key we use for HMAC calculation to
                    # "{{resolve:secretsmanager:${SecretKey}}}" which is pretty silly, but this only happens during
                    # testing, and any constant value is fine, so sure, let's use that.
                    api_props = properties["Events"]["ApiEvent"]["Properties"]
                    env_vars = properties.get("Environment", {}).get("Variables", {})
                    function = Function(
                        properties["CodeUri"],
                        properties["Handler"],
                        self.compile_path(api_props["Path"]),
                        api_props["Method"],
                        policies,
                        env_vars,
                    )
                    self.functions.append(function)

        boto3.resource = self
        boto3.client = self
        jwt.decode = hack_jwt_decode
        jwt.PyJWKClient = Mock()

    def __call__(self, resource: str):
        """Dynamodb and s3 are the only supported resources"""
        assert resource in ["dynamodb", "s3"]
        return self

    def Table(self, name: TableName) -> Table:
        """Fetch a dynamodb table by name"""
        return self.tables[name]

    def put_object(self, Bucket: str, Key: str, Body: str) -> None:
        """Save an object in s3"""
        self.s3_objects[Key] = Body

    def list_objects_v2(self, Bucket: str, Prefix: str) -> dict[str, Any]:
        """List all objects under the prefix"""
        keys = [{"Key": key} for key in self.s3_objects if key.startswith(Prefix)]
        return {"Contents": keys}

    def get_object(self, Bucket: str, Key: str):
        """Fetch an object from s3"""
        body = Mock()
        body.read.return_value = self.s3_objects[Key]
        return {"Body": body}

    def delete_objects(self, Bucket: str, Delete: dict[str, Any]) -> None:
        """Delete objects from s3"""
        for key_dict in Delete["Objects"]:
            del self.s3_objects[key_dict["Key"]]

    def generate_presigned_url(self, ClientMethod: str, Params: dict[str, Any], ExpiresIn: int) -> str:
        """Generate a mock presigned URL for downloading a mock file"""
        return f"https://example.com/{Params['Key']}?auth_id=1234567890"

    def batch_get_item(self, RequestItems: dict) -> dict:
        """Execute a batch of item fetches"""
        result = {"UnprocessedKeys": [], "Responses": {}}
        for table_name, keys_dict in RequestItems.items():
            table = self.tables[table_name]
            result["Responses"][table_name] = []
            for key_dict in keys_dict["Keys"]:
                response = table.get_item(Key=key_dict)
                if "Item" in response:
                    result["Responses"][table_name].append(response["Item"])
        return result

    def apply_policies(self, function: Function) -> None:
        """Apply a function's security policies to the tables"""
        # Set the environment variables
        for env_var, table in function.env_vars.items():
            os.environ[env_var] = table

        # Set the policies
        for policy, table in function.policies:
            self.tables[table].policy = policy

    def call_func(self, path: str, method: str, headers, body: str, params: dict | str = "") -> dict:
        """Execute a lambda function from a web server request"""
        event = {
            "body": body,
            "headers": headers,
            "requestContext": {"http": {"method": method.upper(), "sourceIp": "1.2.3.4"}},
        }

        if isinstance(params, dict):
            event["rawQueryString"] = urlencode(params, doseq=True)
        elif params:
            event["rawQueryString"] = params

        for function in self.functions:
            if method == function.method:
                match = function.path.search(path)
                if match:
                    if match.groupdict():
                        event["pathParameters"] = match.groupdict()
                    self.apply_policies(function)

                    user_id = headers.get("authorization")
                    if user_id and user_id.startswith("Bearer "):
                        user_id = user_id[7:]
                    user = self.users.get(user_id)
                    if user:
                        event["requestContext"] = {"authorizer": {"jwt": {"claims": {"sub": user_id}}}}
                        groups = self.users[UserId(user_id)]
                        if groups:
                            event["requestContext"]["authorizer"]["jwt"]["claims"]["cognito:groups"] = (
                                "[%s]" % " ".join(groups)
                            )

                    return function(event, {})

        return {"statusCode": HTTPStatus.NOT_FOUND, "headers": {"content-type": "application/json"}}

    def launch_server(self, port: int) -> None:
        """Run the web server as a daemon"""
        httpd = HTTPServer(("", port), RequestHandler)
        thread = Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        sleep(DELAY_SERVER_START)
