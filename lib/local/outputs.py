import boto3
import logging
import re

# Constants:
LOG = logging.getLogger(__name__)
CASE_CHANGE = re.compile(r"(.)([A-Z][a-z]+)")
CASE_CHANGE_WITH_DIGITS = re.compile(r"([a-z0-9])([A-Z])")


# For reasons that I do not comprehend, AWS Sam doesn't allow underscores in the output identifiers, so you can't put
# your identifiers in snake case, which would be appropriate for Python identifiers. So, I use the following function to
# convert the CamelCase names to snake_case.
def camel_to_snake(text: str) -> str:
    """Convert a camelCase string to snake_case"""
    # Match a lowercase letter/digit followed by an uppercase letter
    # Insert an underscore between them, then convert everything to lowercase
    return CASE_CHANGE_WITH_DIGITS.sub(r"\1_\2", CASE_CHANGE.sub(r"\1_\2", text)).lower()


def get_outputs_dict(stack_name: str) -> dict[str, str]:
    """Fetch the outputs from AWS sam as a dictionary"""
    cloud_formation = boto3.client("cloudformation")
    response = cloud_formation.describe_stacks(StackName=stack_name)
    # Convert dictionary keys from CamelCase to snake_case
    return {camel_to_snake(output["OutputKey"]): output["OutputValue"] for output in response["Stacks"][0]["Outputs"]}
