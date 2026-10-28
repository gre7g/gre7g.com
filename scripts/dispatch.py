from argparse import ArgumentParser, Namespace
import boto3
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
import json
import logging
import os
import re
from secrets import token_hex
from shutil import which
from subprocess import Popen, PIPE, check_output, check_call
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile
from time import monotonic
import yaml
from unittest.mock import Mock

try:
    import pytest
except ImportError:
    pytest = None  # type: ignore

# Constants:
LOG = logging.getLogger(__name__)
LOG_LEVELS = {
    -1: [logging.ERROR, "ERROR"],
    0: [logging.WARNING, "WARNING"],
    1: [logging.INFO, "INFO"],
    2: [logging.DEBUG, "DEBUG"],
}
STACK_NAME_TEMPLATE = "gre7g-com-%s"
ROOT_PATH = Path(__file__).parents[1]
YAML_PATH = ROOT_PATH / "audit_log" / "save_state.yaml"
VERSION = 1
DIST_PATH = ROOT_PATH / "dist"
INDEX_PATH = DIST_PATH / "index.html"
ASSETS_PATH = DIST_PATH / "assets"
TEST_PATH = ROOT_PATH / "tests"
INTEGRATION_PATH = TEST_PATH / "integration"
STATIC_TEST_PATH = TEST_PATH / "static"
LIB_PATH = ROOT_PATH / "gre7g_lib"
STATIC_PATH = ROOT_PATH / "static"
TEMPLATE_YAML = ROOT_PATH / "template.yaml"
VITE_CONFIG_PATH = ROOT_PATH / "vite.config.ts"
CONFIG_FILENAME = "config.json"
UNIT_TESTER = ["unittest", "discover"]
DELETE_OLDER = timedelta(days=30)
WEB_PORT = 8080
SEARCH_MINIFY = re.compile(r"^\s*minify: (\w+)", re.M)
SEARCH_PRETTIER_EXT = re.compile(r"\.(ts|html|json)$", re.M)

# Globals
G_PY_TESTER = ["pytest"]
G_TESTER = G_PY_TESTER if pytest else UNIT_TESTER

# Libraries
paths = [str(LIB_PATH), str(ROOT_PATH)]
sys.path.extend(paths)
os.environ["PYTHONPATH"] = os.pathsep.join(paths)

from gre7g_lib.audit import configure_audit_log, SourceHash, AUDIT_LOG
from gre7g_lib.boto3_hack import HackBoto
from gre7g_lib.db_defaults import write_default_data_to_db
from gre7g_utils import UserId
from gre7g_lib.outputs import get_outputs_dict
from gre7g_lib.users import REG_USER_ID, ADMIN_USER_ID, ADMIN_GROUP_NAME, CognitoUser, USER_EMAIL
from gre7g_lib.web_server import WebBrowser


def compile_ts(minify: bool = True) -> None:
    """Compile the Typescript code into Javascript"""
    with VITE_CONFIG_PATH.open("rt") as file_obj:
        text = file_obj.read()
    match = SEARCH_MINIFY.search(text)
    assert match
    text = text[: match.start(1)] + str(minify).lower() + text[match.end(1) :]
    with VITE_CONFIG_PATH.open("wt") as file_obj:
        file_obj.write(text)
    check_call([which("npx"), "vite", "build"], cwd=ROOT_PATH)


# Note: Many of the functions below accept a `dest_dict` as a parameter. This is a dictionary pulled from
# `audit_log/save_state.yaml` and is formatted as such:
# {
#     "git-describe": str,
#     "hash": str,
#     "outputs": {
#         "api_endpoint": str,
#         ... (all the sam outputs)
#     },
#     "tests-passed": bool,
#     "timestamp": str in ISO format,
#     "up": bool,  (not present in production)
# }
def setup_sample_data(dest_dict: dict) -> None:
    """Create some sample data in the databases for webserver mode"""
    # Databases
    dynamodb = boto3.resource("dynamodb")
    outputs = dest_dict["outputs"]
    products_table = dynamodb.Table(outputs["products_table_name"])
    carts_table = dynamodb.Table(outputs["carts_table_name"])
    orders_table = dynamodb.Table(outputs["orders_table_name"])
    user_id = UserId(REG_USER_ID)
    write_default_data_to_db(user_id, products_table, carts_table, orders_table)


@dataclass
class Dispatch:
    """Class for building, deploying, and running test suites"""

    args: Namespace
    log_level_name: str

    save_state: dict = field(default_factory=dict)  # see `audit_log/save_state.yaml`

    # Executables
    sam_path: str | None = which("sam")
    git_path: str | None = which("git")
    aws_path: str | None = which("aws")
    npm_path: str | None = which("npm")
    npx_path: str | None = which("npx")

    name_set: str = ""  # Current dev name e.g. "gre7g"
    stack_name: str = ""  # Current stack name e.g. "gre7g-com-gre7g" or "gre7g-com-PROD"
    git_describe: str = ""
    hash_str: str = ""
    stdout: Mock = field(default_factory=Mock)

    def _update_version(self) -> None:
        """Check the version number in save_state member and update if needed"""
        if "version" in self.save_state:
            assert self.save_state["version"] == VERSION
        else:
            self.save_state = {"version": VERSION}

    def load_state(self) -> None:
        """Load the saved state from `audit_log/save_state.yaml`"""
        if not self.args.reset:
            try:
                with open(YAML_PATH, "rt") as file_obj:
                    self.save_state = yaml.safe_load(file_obj)
            except Exception as error:
                LOG.warning("%s: Failed to load YAML state file", error)

        self._update_version()

    def set_stack_name(self, prod: bool = False) -> None:
        """Set the stack name"""
        if prod:
            self.name_set = "PROD"
        else:
            self.name_set = self.save_state.get("dev-stack", {}).get("name-set")
            assert self.name_set, "set stack name first"
        self.stack_name = STACK_NAME_TEMPLATE % self.name_set

    def describe(self) -> None:
        """Fetch the git describe"""
        assert self.git_path
        self.git_describe = check_output(
            [self.git_path, "describe", "--tags", "--always", "--dirty"], text=True
        ).strip()

    def set_hash(self) -> None:
        """Calculate a hash for the source files"""
        self.hash_str = SourceHash().get_hash()

    def call(self, *args, **kwargs) -> int:
        """Call an executable command, filtering the output as needed"""
        # Note: The stdout filtering isn't working as expected, but oh well. Not an important feature.
        kwargs = {"stdout": self.stdout, "stderr": sys.stderr} | kwargs
        return Popen(*args, **kwargs).wait()

    def build(self) -> bool:
        """Run `sam build`, return build success"""
        return_code = 0
        # Have the source files changed?
        if self.hash_str != self.save_state.setdefault("build", {}).get("hash"):
            # Yes, rebuild
            assert self.sam_path, "unable to find AWS sam"
            return_code = self.call([self.sam_path, "build"], cwd=ROOT_PATH, stdout=self.stdout, stderr=sys.stderr)
            build = self.save_state.setdefault("build", {})
            build["success-last"] = not return_code
            build["hash"] = self.hash_str
            assert return_code == 0, "build failed"

        return return_code == 0

    def check_call(self, *args, **kwargs) -> None:
        """Call an executable command, throw an exception on failure"""
        assert self.call(*args, **kwargs) == 0

    def login_call(self, command: list[str]) -> None:
        """Call an executable command, log in if necessary"""
        process = Popen(command, cwd=ROOT_PATH, stdout=self.stdout, stderr=PIPE, text=True)
        stdout, stderr = process.communicate()
        sys.stderr.write(stderr)
        if process.returncode:
            if ("Please reauthenticate using 'aws login'." in stderr) or ("The provided token has expired." in stderr):
                self.check_call([self.aws_path, "login"], stdout=self.stdout, stderr=sys.stderr)
                self.check_call(command, stdout=self.stdout, stderr=sys.stderr)  # TODO: what if no changes?
            elif "No changes to deploy." in stderr:
                pass
            else:
                assert False, "unexpected error"

    def delete(self, dest_dict: dict) -> None:
        """Delete the dev stack"""
        assert self.sam_path, "unable to find AWS sam"
        web_file_storage = dest_dict.get("outputs", {}).get("web_file_storage")
        self.login_call([self.aws_path, "s3", "rm", f"s3://{web_file_storage}", "--recursive"])
        self.check_call([self.sam_path, "delete", "--stack-name", self.stack_name])

    def deploy(self, dest_dict: dict) -> None:
        """Deploy the stack, update the `dest_dict`"""
        assert self.sam_path, "unable to find AWS sam"
        production = str(self.name_set == "PROD").lower()
        self.login_call(
            [
                self.sam_path,
                "deploy",
                "--stack-name",
                self.stack_name,
                "--parameter-overrides",
                f"EnableDeletionProtection={production},SecretKey={token_hex()}",
            ]
        )
        self.describe()
        self.record_deployment(dest_dict)
        self.patch_cognito(dest_dict)
        self.sync_static_files(dest_dict)
        self.copy_config(dest_dict)
        self.invalidate_cache(dest_dict.get("outputs", {}).get("web_distribution"))

    def record_deployment(self, dest_dict: dict) -> None:
        """Save some deployment details"""
        dest_dict.update(
            {
                "hash": self.hash_str,
                "timestamp": datetime.now(UTC).isoformat(),
                "git-describe": self.git_describe,
                "outputs": get_outputs_dict(self.stack_name),
            }
        )

    def patch_cognito(self, dest_dict: dict) -> None:
        """Fix the temporary callback URL"""
        # If you look in `template.yaml` under Resources/UserPoolClient/Properties/CallbackURLs, you'll find a templated
        # value of `https://%%CLOUDFRONT_DOMAIN%%`. Normally, we would use a !Sub to fill in the correct value, but
        # putting that in there results in a loop that AWS sam cannot resolve. The simplest solution is to use the
        # templated placeholder and then update the value in a subsequent step. This isn't ideal, obviously, but it
        # works.

        # Read current configuration
        outputs = dest_dict.setdefault("outputs", {})
        assert self.aws_path
        client_config = json.loads(
            check_output(
                [
                    self.aws_path,
                    "cognito-idp",
                    "describe-user-pool-client",
                    "--no-cli-pager",
                    "--user-pool-id",
                    outputs["user_pool"],
                    "--client-id",
                    outputs["user_pool_client"],
                ]
            )
        )

        # This gives us more information than we'll need by nesting it in a dictionary and including some timestamps
        # that are read-only. Adjust the data now.
        client_config = client_config["UserPoolClient"]
        del client_config["CreationDate"]
        del client_config["LastModifiedDate"]

        # Replace the callback URLs
        client_config["CallbackURLs"] = [outputs.get("website_url")]

        # Write the configuration to a temporary file
        with NamedTemporaryFile(mode="wt", delete_on_close=False) as temp_file:
            json.dump(client_config, temp_file)
            temp_file.close()

            # The AWS command to upload this JSON requires a file:// syntax instead of a file path, so we need to
            # convert.
            file_path = f"file://{temp_file.name.replace(os.sep, '/')}"

            # Upload new configuration
            self.check_call(
                [
                    self.aws_path,
                    "cognito-idp",
                    "update-user-pool-client",
                    "--no-cli-pager",
                    "--cli-input-json",
                    file_path,
                ]
            )

    def sync_static_files(self, dest_dict: dict) -> None:
        """Copy all images, stylesheets, scripts, and HTML to the S3 bucket"""
        web_file_storage = dest_dict.get("outputs", {}).get("web_file_storage")
        self.check_call([self.aws_path, "s3", "cp", str(INDEX_PATH), f"s3://{web_file_storage}/index.html"])
        self.check_call([self.aws_path, "s3", "sync", str(STATIC_PATH), f"s3://{web_file_storage}"])
        self.check_call([self.aws_path, "s3", "sync", str(ASSETS_PATH), f"s3://{web_file_storage}/assets/"])

    def copy_config(self, dest_dict: dict) -> None:
        """Copy the sam outputs to a configuration file and upload"""
        # Write outputs to a temporary file
        outputs = dest_dict.get("outputs", {})
        with NamedTemporaryFile("wt", delete_on_close=False) as temp_file:
            temp_file.write(json.dumps(outputs))
            temp_file.close()

            # Copy the file to S3
            web_file_storage = outputs.get("web_file_storage")
            self.check_call([self.aws_path, "s3", "cp", temp_file.name, f"s3://{web_file_storage}/{CONFIG_FILENAME}"])

    def invalidate_cache(self, distribution: str) -> None:
        """Invalidate the cache so latest web files are served"""
        self.check_call(
            [self.aws_path, "cloudfront", "create-invalidation", "--distribution-id", distribution, "--paths", "/*"]
        )

    def static_tests(self) -> None:
        """Run the static tests"""
        args = [sys.executable, "-m"] + G_TESTER + [str(STATIC_TEST_PATH)]
        self.check_call(args)

        assert self.npx_path
        process = Popen([self.npx_path, "prettier", str(ROOT_PATH), "--check"], text=True, stdout=PIPE, stderr=PIPE)
        _, stderr = process.communicate()
        warnings = [line for line in stderr.splitlines() if SEARCH_PRETTIER_EXT.search(line)]
        if warnings:
            print("Prettier found issues:")
            print("\n".join(warnings))
            assert False

    def typescript_tests(self) -> None:
        """Run the typescript tests"""
        self.check_call([self.npm_path, "run", "test"])

    def integration_tests(self, stack_name: str) -> bool:
        """Run the integration tests"""
        args = [sys.executable, "-m"] + G_TESTER + [str(INTEGRATION_PATH)]
        return self.call(args, env=os.environ | {"STACK-NAME": stack_name}) == 0

    @staticmethod
    def set_password(dest_dict: dict) -> None:
        """Set a random password for the regular user and print to screen"""
        outputs = dest_dict["outputs"]
        user = CognitoUser(outputs["user_pool"], outputs["user_pool_client"], USER_EMAIL)
        user.set_password()
        print(f"Website: {outputs['website_url']}")
        print(f"User: {USER_EMAIL}")
        print(f"Password: {user.password}")

    def main(self) -> int:
        """Dispatch a build, deploy, and run the tests"""
        passed = 0
        audit_log = Mock()
        self.load_state()
        try:
            if self.args.name:
                self.save_state.setdefault("dev-stack", {})["name-set"] = self.args.name

            if self.args.brief:
                self.name_set = "BRIEF"
                self.typescript_tests()
                self.check_call(
                    [sys.executable, "-m"] + G_TESTER + [str(INTEGRATION_PATH)],
                    env=os.environ | {"STACK-NAME": "BRIEF"},
                )

            elif self.args.local:
                self.name_set = "LOCAL"
                self.typescript_tests()
                self.check_call(
                    [sys.executable, "-m"] + G_TESTER + [str(TEST_PATH)],
                    env=os.environ | {"STACK-NAME": "LOCAL"},
                )

            elif self.args.dev and (self.args.command == "down"):
                self.set_stack_name()
                stack = (
                    self.save_state.setdefault("dev-stack", {}).setdefault("recent", {}).setdefault(self.name_set, {})
                )
                self.delete(stack)
                stack["up"] = False

            elif self.args.dev and (self.args.command == "up"):
                self.static_tests()
                self.typescript_tests()
                compile_ts()
                audit_log = AUDIT_LOG
                self.set_hash()
                audit_log.info("dispatch %r on hash %s", self.args, self.hash_str)
                self.set_stack_name()
                success = self.build()
                audit_log.info("build success: %r", success)
                stack = (
                    self.save_state.setdefault("dev-stack", {}).setdefault("recent", {}).setdefault(self.name_set, {})
                )
                if not ((self.hash_str == stack.get("hash")) and stack.get("up")):
                    self.deploy(stack)
                    audit_log.info("deploy success")
                    stack["up"] = True
                passed = self.integration_tests(self.stack_name)
                stack["tests-passed"] = passed
                audit_log.info("tests passed: %r", passed)
                assert passed, "tests failed"
                setup_sample_data(stack)
                self.set_password(stack)

            elif self.args.prod:
                audit_log = AUDIT_LOG
                self.describe()
                assert "-dirty" not in self.git_describe, "commit all changes before deploying to production"
                assert self.git_path
                branch_name = check_output([self.git_path, "branch", "--show-current"]).strip()
                assert branch_name == "master", "only the master branch should be deployed to production"
                self.static_tests()
                self.typescript_tests()
                compile_ts()
                self.set_hash()
                audit_log.info("dispatch %r on hash %s", self.args, self.hash_str)
                dev_name = self.save_state.get("dev-stack", {}).get("name-set")
                dev_stack = self.save_state.get("dev-stack", {}).get("recent", {}).get(dev_name, {})
                assert self.hash_str == dev_stack.get("hash"), "deploy to dev before deploying to production"
                assert dev_stack.get("tests-passed"), "tests must pass on dev before deploying to production"
                success = self.build()
                audit_log.info("build success: %r", success)
                production = self.save_state["production"]
                if self.hash_str != self.save_state.setdefault("production", {}).get("hash"):
                    self.deploy(production)
                    audit_log.info("deploy success")
                passed = self.integration_tests("PROD")
                production["tests-passed"] = passed
                audit_log.info("tests passed: %r", passed)
                assert passed, "tests failed"
                setup_sample_data(production)
                self.set_password(production)

        except Exception as error:
            audit_log.error("failed: %s", error)
            LOG.exception(error)
            passed = 1
        else:
            audit_log.info("complete")
        finally:
            # Are there any old deployments we can purge from the saved state? We don't want this to grow endlessly.
            delete_older_than = (datetime.now(UTC) - DELETE_OLDER).isoformat()
            recent_stacks = self.save_state.setdefault("dev-stack", {}).setdefault("recent", {})
            # Get a list of keys to delete first so we don't modify while we're looping
            old_stack_names = [
                key for key, values in recent_stacks.items() if values.get("timestamp", "0") < delete_older_than
            ]
            for stack_name in old_stack_names:
                del recent_stacks[stack_name]

            # Write the saved state back out
            with open(YAML_PATH, "wt") as file_obj:
                yaml.dump(self.save_state, file_obj)

        return passed


def main():
    """Main function"""
    # Parse commandline arguments
    arg_parser = ArgumentParser()
    arg_parser.add_argument("-v", "--verbose", action="count", default=0)
    arg_parser.add_argument("-q", "--quiet", action="store_const", dest="verbose", const=-1)
    arg_parser.add_argument("-n", "--name", action="store", help="set development name")
    arg_parser.add_argument("-r", "--reset", action="store_true", help="reset saved variables")

    destination_group = arg_parser.add_mutually_exclusive_group()
    destination_group.add_argument("-b", "--brief", action="store_true", help="run quick with basic checks only")
    destination_group.add_argument("-l", "--local", action="store_true", help="run locally with better checking")
    destination_group.add_argument("-d", "--dev", action="store_true", help="deploy to development")
    destination_group.add_argument("-p", "--prod", action="store_true", help="deploy to production")

    arg_parser.add_argument("command", nargs="?", help="bring the dev stack up (default) or down")

    args = arg_parser.parse_args()

    # Enable logging
    log_level, level_name = LOG_LEVELS.get(max(2, args.verbose), logging.DEBUG)  # noqa
    logging.basicConfig(level=log_level)
    for mouthy_log in ["boto3", "botocore", "urllib3"]:
        logging.getLogger(mouthy_log).setLevel(logging.WARNING)
    configure_audit_log(log_level <= logging.INFO)
    G_PY_TESTER.extend(["--log-cli-level", level_name])

    # Sanitize incompatible combinations of options
    if args.command not in ["up", "down", "regular", "admin", "webserver", None]:
        arg_parser.error("valid commands: up, down, regular, admin")
    if args.command == "down":
        if args.prod or args.brief or args.local:
            arg_parser.error("this tool can only delete a development stack")
        else:
            args.dev = True
    elif args.command == "up":  # explicit
        if args.brief or args.local:
            arg_parser.error("can't bring a local stack up")
        elif not args.prod:
            args.dev = True
    elif not args.command:
        args.command = "up"
    if not (args.local or args.dev or args.prod or (args.command != "up")):
        args.brief = True

    # Run a webserver?
    if args.command in ["regular", "admin", "webserver"]:
        compile_ts(False)
        HackBoto(TEMPLATE_YAML, {REG_USER_ID: [], ADMIN_USER_ID: [ADMIN_GROUP_NAME]}).apply_hack()  # type: ignore
        user_ids = {"regular": REG_USER_ID, "admin": ADMIN_USER_ID, "webserver": None}
        user_id = user_ids[args.command]
        setup_sample_data(
            {
                "outputs": {
                    "carts_table_name": "CartsTable",
                    "orders_table_name": "OrdersTable",
                    "products_table_name": "ProductsTable",
                }
            }
        )
        WebBrowser(WEB_PORT).run_main_thread(user_id)
    else:
        # No, build/deploy/test
        dispatch = Dispatch(args, level_name)
        if log_level < logging.WARNING:
            dispatch.stdout = sys.stdout  # noqa
        start_time = monotonic()
        exit_code = dispatch.main()
        elapsed = monotonic() - start_time
        LOG.info("elapsed: %0.3f seconds", elapsed)
        sys.exit(exit_code)


if __name__ == "__main__":
    main()
# TODO set secret string as a random parameter and generate it before deploy
