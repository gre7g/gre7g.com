"""Various utilities used in lambdas and testing"""

from abc import ABC, abstractmethod
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext
import boto3
from botocore.exceptions import ClientError
from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import auto, StrEnum
from http import HTTPStatus
from itertools import batched
import json
import logging
import os
from types_boto3_dynamodb.service_resource import Table as DynamoDBTable
from typing import Any, Self, NewType, Callable
from uuid import uuid1

# Types:
UserId = NewType("UserId", str)
ListId = NewType("ListId", str)
ItemId = NewType("ItemId", str)
Timestamp = NewType("Timestamp", str)
Watchlist = NewType("Watchlist", dict[UserId | ListId, Timestamp])
GroupTag = NewType("GroupTag", str)

# Constants:
LOG = Logger(__name__) if os.getenv("AWS_LAMBDA_FUNCTION_NAME") else logging.getLogger(__name__)
ROOT_GROUP = GroupTag("root")
TABLE_VERSION = 1
MAX_ITEMS_PER_BATCH = 100


class AuthenticationRequired(StrEnum):
    """Authentication required at the lambda level"""

    # Basic rights
    NONE = auto()
    ACTIVE_USER = auto()

    # System rights
    ROOT_USER = auto()

    # Rights for an existing list
    READ_LIST = auto()
    WRITE_LIST = auto()
    OWNER_ADMIN_LIST = auto()


class Privilege(StrEnum):
    """List access privileges"""

    NONE = auto()
    READ_ONLY = auto()
    READ_WRITE = auto()
    ADMIN = auto()


class Ownership(StrEnum):
    """For tracking a list's origin"""

    OWNER = auto()
    SHARED_TO_OTHERS = auto()
    SHARED_FROM_OTHER = auto()


@dataclass
class Upgradeable:
    """Base class for a table row with a version number"""

    @classmethod
    def upgrade(cls, version: int, value_dict: dict[str, Any]) -> dict[str, Any]:
        """Upgrade a table row to the current version"""
        assert version <= TABLE_VERSION, "Data is from a future version"
        while version < TABLE_VERSION:
            upgrader = f"upgrade_{version}_to_{version + 1}"
            if hasattr(cls, upgrader):
                value_dict = getattr(cls, upgrader)(value_dict)
            version += 1
        return value_dict

    def to_dict(self) -> dict[str, Any]:
        """Convert the object to a dict"""
        raise NotImplementedError

    def put(self, db_table: DynamoDBTable) -> None:
        """Put object into table"""
        assert db_table
        db_table.put_item(Item=self.to_dict())


@dataclass
class ListIdAndPriv(Upgradeable):
    """A list identify and the granted privilege level for that list"""

    list_id: ListId = ListId("")
    privilege: Privilege = Privilege.NONE
    ownership: Ownership = Ownership.OWNER

    @classmethod
    def from_dict(cls, version: int, value_dict: dict[str, Any]) -> Self:
        """Generate an object from a dict"""
        value_dict = cls.upgrade(version, value_dict)
        list_id = value_dict["list_id"]
        privilege_str = value_dict["privilege"]
        owner = value_dict["ownership"]
        assert isinstance(list_id, str)
        assert isinstance(privilege_str, str)
        assert isinstance(owner, str)
        return cls(ListId(list_id), getattr(Privilege, privilege_str), getattr(Ownership, owner))

    def to_dict(self) -> dict[str, Any]:
        """Convert the object to a dict"""
        return {"list_id": self.list_id, "privilege": self.privilege.name, "ownership": self.ownership.name}


@dataclass
class User(Upgradeable):
    """A user and the lists it can access"""

    user_id: UserId
    active: bool = True
    lists: dict[ListId, ListIdAndPriv] = field(default_factory=dict)  # type: ignore
    version: int = TABLE_VERSION

    @classmethod
    def from_dict(cls, version: int, value_dict: dict[str, Any]) -> Self:
        """Generate an object from a dict"""
        value_dict = cls.upgrade(version, value_dict)
        user_id = value_dict["user_id"]
        active = value_dict["active"]
        lists_dict = value_dict["lists"]
        assert isinstance(user_id, str)
        assert isinstance(active, bool)
        assert isinstance(lists_dict, dict)
        lists = {list_id: ListIdAndPriv.from_dict(version, list_dict) for list_id, list_dict in lists_dict.items()}
        return cls(UserId(user_id), active, lists)

    def to_dict(self) -> dict[str, Any]:
        """Convert the object to a dict"""
        lists_dict = {list_id: list_item.to_dict() for list_id, list_item in self.lists.items()}
        return {"user_id": self.user_id, "active": self.active, "lists": lists_dict, "version": TABLE_VERSION}

    def to_key(self) -> dict[str, Any]:
        """Return the table key as a dict"""
        return {"user_id": self.user_id}

    @classmethod
    def get(cls, user_acl_table: DynamoDBTable, user_id: UserId) -> Self:
        """Get object from table"""
        assert user_acl_table
        response = user_acl_table.get_item(Key={"user_id": user_id})
        try:
            value_dict = response["Item"]
            version = int(value_dict["version"])  # type: ignore [arg-type]
            user = cls.from_dict(version, value_dict)
        except:
            user = cls(user_id)
        return user


@dataclass
class ListEntry(Upgradeable):
    """One entry in a list"""

    item: str
    user_updated: UserId
    checked: bool = False
    item_id: ItemId = field(default_factory=lambda: ItemId(uuid1().hex))
    updated_at: Timestamp = field(default_factory=lambda: Timestamp(datetime.now(UTC).isoformat()))

    @classmethod
    def from_dict(cls, version: int, value_dict: dict[str, Any]) -> Self:
        """Generate an object from a dict"""
        value_dict = cls.upgrade(version, value_dict)
        item = value_dict["item"]
        user_updated = value_dict["user_updated"]
        checked = value_dict["checked"]
        item_id = value_dict["item_id"]
        updated_at = value_dict["updated_at"]
        assert isinstance(item, str)
        assert isinstance(user_updated, str)
        assert isinstance(checked, bool)
        assert isinstance(item_id, str)
        assert isinstance(updated_at, str)
        return cls(item, UserId(user_updated), checked, ItemId(item_id), Timestamp(updated_at))

    def to_dict(self) -> dict[str, Any]:
        """Convert the object to a dict"""
        return {
            "item": self.item,
            "user_updated": self.user_updated,
            "checked": self.checked,
            "item_id": self.item_id,
            "updated_at": self.updated_at,
        }


@dataclass
class TodoList(Upgradeable):
    """A to-do list"""

    name: str = ""
    user_ids: list[UserId] = field(default_factory=list)
    list_id: ListId = field(default_factory=lambda: ListId(uuid1().hex))
    items: list[ListEntry] = field(default_factory=list)
    version: int = TABLE_VERSION

    @classmethod
    def from_dict(cls, version: int, value_dict: dict[str, Any]) -> Self:
        """Generate an object from a dict"""
        value_dict = cls.upgrade(version, value_dict)
        name = value_dict["name"]
        user_ids = value_dict["user_ids"]
        list_id = value_dict["list_id"]
        item_dicts = value_dict["items"]
        assert isinstance(name, str)
        assert isinstance(user_ids, list)
        assert isinstance(list_id, str)
        assert isinstance(item_dicts, list)
        assert all(isinstance(item, dict) for item in item_dicts)
        items = [ListEntry.from_dict(version, item_dict) for item_dict in item_dicts]
        assert all(isinstance(user_id, str) for user_id in user_ids)
        return cls(name, user_ids, ListId(list_id), items)

    def to_dict(self) -> dict[str, Any]:
        """Convert the object to a dict"""
        item_dicts = [item.to_dict() for item in self.items]
        return {
            "name": self.name,
            "user_ids": self.user_ids,
            "list_id": self.list_id,
            "items": item_dicts,
            "version": TABLE_VERSION,
        }

    def to_key(self) -> dict[str, Any]:
        """Return the table key as a dict"""
        return {"list_id": self.list_id}

    @classmethod
    def get(cls, list_table: DynamoDBTable, list_id: ListId) -> Self:
        """Get object from table"""
        assert list_table
        response = list_table.get_item(Key={"list_id": list_id})
        try:
            value_dict = response["Item"]
            version = int(value_dict["version"])  # type: ignore [arg-type]
            todo_list = cls.from_dict(version, value_dict)
        except:
            todo_list = cls()
        return todo_list


@dataclass
class LastUpdate(Upgradeable):
    """A row describing when another row was last updated"""

    user_or_list_id: UserId | ListId
    timestamp: Timestamp = field(default_factory=lambda: Timestamp(datetime.now(UTC).isoformat()))
    version: int = TABLE_VERSION

    @classmethod
    def from_dict(cls, version: int, value_dict: dict[str, Any]) -> Self:
        """Generate an object from a dict"""
        value_dict = cls.upgrade(version, value_dict)
        user_or_list_id = value_dict["id"]
        timestamp = value_dict["timestamp"]
        assert isinstance(user_or_list_id, str)
        assert isinstance(timestamp, str)
        return cls(user_or_list_id, Timestamp(timestamp))  # type: ignore

    def to_dict(self) -> dict[str, Any]:
        """Convert the object to a dict"""
        return {"id": self.user_or_list_id, "timestamp": self.timestamp, "version": TABLE_VERSION}

    def to_key(self) -> dict[str, Any]:
        """Return the table key as a dict"""
        return {"id": self.user_or_list_id}

    @classmethod
    def get(cls, last_update_table: DynamoDBTable, user_or_list_id: UserId | ListId) -> Self:
        """Get object from table"""
        assert last_update_table
        response = last_update_table.get_item(Key={"id": user_or_list_id})
        try:
            value_dict = response["Item"]
            version = int(value_dict["version"])  # type: ignore [arg-type]
            last_update = cls.from_dict(version, value_dict)
        except:
            last_update = cls(user_or_list_id)
        return last_update


@dataclass
class LambdaBase(ABC):
    """Base class for lambdas"""

    user_acl_table: Any = None
    list_table: Any = None
    timestamp_table: Any = None

    path_parameters: dict = field(default_factory=dict)
    list_id: ListId | None = None
    item_id: ItemId | None = None
    user_id: UserId | None = None
    groups: list[GroupTag] = field(default_factory=list)
    root: bool = False

    user: User | None = None
    todo_list: TodoList | None = None

    AUTH_REQUIRED = AuthenticationRequired.READ_LIST

    @abstractmethod
    def handler(self, event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
        """Overload this function with your handler code"""
        raise NotImplementedError

    def wrapper(self, event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
        """Wrapper around the handler than takes care of parameters, privileges, and error handling"""
        try:
            self.path_parameters = event.get("pathParameters") or {}
            self.list_id = self.path_parameters.get("list_id")
            self.item_id = self.path_parameters.get("item_id")
            claims = event.get("requestContext", {}).get("authorizer", {}).get("jwt", {}).get("claims", {})
            self.user_id = claims.get("sub")
            group_str = claims.get("cognito:groups")
            self.groups = group_str[1:-1].split(" ") if group_str else []
            self.root = ROOT_GROUP in self.groups

            if self.AUTH_REQUIRED == AuthenticationRequired.NONE:
                pass
            else:
                self.user = User.get(self.user_acl_table, self.user_id)
                if not self.user.active:
                    raise PermissionError()
                privilege = self.user.lists.get(self.list_id or ListId(""), ListIdAndPriv()).privilege

                match self.AUTH_REQUIRED:
                    case AuthenticationRequired.ACTIVE_USER:
                        pass
                    case AuthenticationRequired.ROOT_USER:
                        if self.root:
                            pass
                        else:
                            raise PermissionError()
                    case AuthenticationRequired.OWNER_ADMIN_LIST:
                        if self.root or (privilege == Privilege.ADMIN):
                            pass
                        else:
                            raise PermissionError()
                    case AuthenticationRequired.READ_LIST:
                        if self.root or (privilege != Privilege.NONE):
                            pass
                        else:
                            raise PermissionError()
                    case AuthenticationRequired.WRITE_LIST:
                        if self.root or (privilege in [Privilege.READ_WRITE, Privilege.ADMIN]):
                            pass
                        else:
                            raise PermissionError()
                    case _:
                        assert False, "unknown authorization type"

            status = HTTPStatus.OK
            body = self.handler(event=event, context=context)

        except ClientError as error:
            LOG.exception(error)
            if error.response["Error"]["Code"] == "ConditionalCheckFailedException":
                status = HTTPStatus.BAD_REQUEST
                body = {"message": "failed update condition"}
            else:
                status = HTTPStatus.INTERNAL_SERVER_ERROR
                body = {"message": error.response["Error"]["Message"]}

        except PermissionError:
            LOG.error("Unauthenticated")
            status = HTTPStatus.FORBIDDEN
            body = {"message": "Forbidden"}

        except KeyError as error:
            LOG.exception("key error")
            status = HTTPStatus.BAD_REQUEST
            body = {"message": str(error)}

        except Exception as error:
            LOG.exception("Unhandled exception")
            status = HTTPStatus.INTERNAL_SERVER_ERROR
            body = {"message": str(error)}

        return {"statusCode": status, "headers": {"content-type": "application/json"}, "body": json.dumps(body)}

    @staticmethod
    def get_table(env_name: str) -> DynamoDBTable | None:
        """Get a dynamodb table"""
        name = os.getenv(env_name)
        return boto3.resource("dynamodb").Table(name) if name else None

    @classmethod
    def lambda_handler(cls) -> Callable | None:
        """A convenience method for instantiating a Lambda handler"""
        try:
            user_acl_table = cls.get_table("USER_ACL_TABLE")
            list_table = cls.get_table("LIST_TABLE")
            timestamp_table = cls.get_table("TIMESTAMP_TABLE")
            return cls(user_acl_table, list_table, timestamp_table).wrapper
        except:
            LOG.exception("loading object failed")
            return None

    def get_todo_list(self) -> None:
        """Get the to-do list"""
        assert self.user
        assert self.list_id

        self.todo_list = TodoList.get(self.list_table, self.list_id)

    def watchlist(self, *ids: ListId) -> dict[str, Watchlist]:
        timestamp_table = os.getenv("TIMESTAMP_TABLE")
        assert timestamp_table
        watchlist = Watchlist({})
        keys = [{"id": name} for name in ((self.user_id,) + ids)]
        for batch in batched(keys, MAX_ITEMS_PER_BATCH):
            response = boto3.resource("dynamodb").batch_get_item(
                RequestItems={timestamp_table: {"Keys": list(batch)}},  # noqa
            )
            assert not response["UnprocessedKeys"]
            for item in response.get("Responses", {}).get(timestamp_table, []):
                watchlist[item["id"]] = item["timestamp"]  # type: ignore [assignment,index]
        return {"watchlist": watchlist}

    def updated(self, *ids: UserId | ListId) -> None:
        """Mark users and/or lists as updated"""
        for id_str in ids:
            LastUpdate(id_str).put(self.timestamp_table)

    def format_list(self) -> dict:
        """Format the to-do list for output"""
        assert self.todo_list
        items = [{"item_id": item.item_id, "text": item.item, "checked": item.checked} for item in self.todo_list.items]
        return {"name": self.todo_list.name, "items": items}
