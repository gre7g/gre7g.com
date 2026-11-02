"""Utility functions for managing users"""

import boto3
from dataclasses import dataclass, field
import logging
from typing import Any, NewType

# Constants:
LOG = logging.getLogger(__name__)
ADMIN_GROUP_NAME = "root"
USER_EMAIL = "user@example.test"
ADMIN_EMAIL = "admin@example.test"
# Randomly chosen values:
REG_USER_ID = "f65b7878-a973-11f1-874a-64d69adcd141"
ADMIN_USER_ID = "0a0ae688-a974-11f1-a41f-64d69adcd141"

# Types:
RegularUser = NewType("RegularUser", "CognitoUser")
AdminUser = NewType("AdminUser", "CognitoUser")


@dataclass
class CognitoUser:
    """Represents a user in Cognito"""

    user_pool: str
    user_pool_client: str
    email: str
    password: str | None = None
    user_id: str | None = None
    access_token: str | None = None
    id_token: str | None = None
    refresh_token: str | None = None

    cognito: Any = field(default_factory=lambda: boto3.client("cognito-idp"))

    def __post_init__(self) -> None:
        """Post initialization code"""
        if self.password is None:
            self.password = boto3.client("secretsmanager").get_random_password()["RandomPassword"]

    def delete(self) -> None:
        """Delete user from Cognito"""
        self.cognito.admin_delete_user(UserPoolId=self.user_pool, Username=self.email)

    def create_user(self) -> None:
        """Create user in Cognito"""
        response = self.cognito.admin_create_user(
            UserPoolId=self.user_pool,
            Username=self.email,
            UserAttributes=[
                {"Name": "email", "Value": self.email},
                {"Name": "email_verified", "Value": "true"},
            ],
            MessageAction="SUPPRESS",
        )
        # Technically, I think you should search through response["User"]["Attributes"] for a list item that's a dict
        # with "Name": "sub" to get "Value", but this is the same data and so much simpler.
        self.user_id = response["User"]["Username"]

        self.set_password()

    def set_password(self) -> None:
        """Set a permanent password for the user"""
        self.cognito.admin_set_user_password(
            UserPoolId=self.user_pool, Username=self.email, Password=self.password, Permanent=True
        )

    def add_admin(self) -> None:
        """Assign admin privileges to a user"""
        self.cognito.admin_add_user_to_group(UserPoolId=self.user_pool, Username=self.email, GroupName=ADMIN_GROUP_NAME)

    def authenticate(self) -> None:
        """Log a user in and get the appropriate authority tokens"""
        response = self.cognito.initiate_auth(
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={"USERNAME": self.email, "PASSWORD": self.password},
            ClientId=self.user_pool_client,
        )
        result = response["AuthenticationResult"]
        self.id_token = result["IdToken"]
        self.access_token = result["AccessToken"]
        self.refresh_token = result["RefreshToken"]

    @classmethod
    def create_users(cls, user_pool: str, user_pool_client: str) -> RegularUser:  # tuple[RegularUser, AdminUser]:
        """Create a privileged user and a regular user"""
        cognito = boto3.client("cognito-idp")

        regular_user = CognitoUser(user_pool, user_pool_client, USER_EMAIL)
        try:
            regular_user.delete()
        except cognito.exceptions.UserNotFoundException:
            pass
        regular_user.create_user()
        regular_user.authenticate()

        # admin_user = CognitoUser(user_pool, user_pool_client, ADMIN_EMAIL)
        # try:
        #     admin_user.delete()
        # except cognito.exceptions.UserNotFoundException:
        #     pass
        # admin_user.create_user()
        # admin_user.add_admin()
        # admin_user.authenticate()

        return RegularUser(regular_user)  # , AdminUser(admin_user)
