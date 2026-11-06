from dataclasses import dataclass, field
from importlib import import_module
import logging
from pathlib import Path
import re
from typing import Any, NewType
import yaml

# Constants:
LOG = logging.getLogger(__name__)
SUB_REF = re.compile(r"!(Ref|Sub|GetAtt|If|Equals)\b")
PARAMETERS = re.compile(r"\{(\w+)}")

# Types:
ROOT_PATH = Path(__file__).parents[2]
EnvVar = NewType("EnvVar", str)
ResourceName = NewType("ResourceName", str)
PolicyName = NewType("PolicyName", str)
Policies = list[tuple[PolicyName, ResourceName]]


@dataclass
class Function:
    """Represents a lambda function in the `template.yaml` file"""

    name: str
    code_uri: str
    handler: str
    path: re.Pattern[str]
    method: str
    timeout: int | None = None
    policies: Policies = field(default_factory=Policies)
    env_vars: dict[EnvVar, ResourceName] = field(default_factory=dict)
    requirements: set[str] = field(default_factory=set)

    def __call__(self, event, context) -> dict:
        """Call the lambda function"""
        path = f"{self.code_uri.replace("/", ".")}.{self.handler}".split(".")
        module = path[:-1]
        function = path[-1]
        return getattr(import_module(".".join(module)), function)(event, context)

    @property
    def file_path(self) -> Path:
        """Get the path to the source file"""
        parts = self.code_uri.split("/") + self.handler.split(".")
        path = ROOT_PATH
        for part in parts[:-1]:
            path = path / part
        return path


@dataclass
class Template:
    """Parsed SAM template"""

    path: Path
    functions: list[Function] = field(default_factory=list)
    template_dict: dict[str, Any] = field(init=False)

    @staticmethod
    def compile_path(path: str) -> re.Pattern[str]:
        """Generates a regular expression pattern for fetching parameters out of an URL path"""
        pattern = PARAMETERS.sub(r"(?P<\1>[\\w-]+)", path)
        return re.compile(f"^{pattern}$")

    def load(self) -> None:
        """Load a template file into a dictionary"""
        with self.path.open("rt") as file_obj:
            template_str = file_obj.read()

        # The YAML library doesn't deal well with !Ref, !Sub, !GetAtt, !If, and !Equals, but that's okay. We don't need
        # them, so just strip them out.
        self.template_dict = yaml.load(SUB_REF.sub("", template_str), yaml.Loader)

        for key, value in self.template_dict["Resources"].items():
            if value["Type"] == "AWS::Serverless::Function":
                properties = value.get("Properties", {})

                # Find policies
                policies = Policies()
                for item in properties.get("Policies", []):
                    policy = next(iter(item))
                    if "TableName" in item[policy]:
                        policies.append((PolicyName(policy), ResourceName(item[policy]["TableName"])))
                    elif "BucketName" in item[policy]:
                        policies.append((PolicyName(policy), ResourceName(item[policy]["BucketName"])))

                # Find environment variables
                api_props = properties["Events"]["ApiEvent"]["Properties"]
                env_vars = properties.get("Environment", {}).get("Variables", {})
                function = Function(
                    key,
                    properties["CodeUri"],
                    properties["Handler"],
                    self.compile_path(api_props["Path"]),
                    api_props["Method"],
                    properties.get("Timeout"),
                    policies,
                    env_vars,
                )
                self.functions.append(function)
