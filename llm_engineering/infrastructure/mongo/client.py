from functools import cache

from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import PyMongoError

from llm_engineering.exceptions import StorageUnavailableError
from llm_engineering.settings.app_settings import get_settings


@cache
def get_client() -> MongoClient:
    """One client per process (MongoClient pools connections itself)."""
    mongo = get_settings().mongo
    client: MongoClient = MongoClient(mongo.connection_string, serverSelectionTimeoutMS=mongo.timeout_ms)
    try:
        client.admin.command("ping")
    except PyMongoError as exc:
        client.close()
        raise StorageUnavailableError(f"cannot reach MongoDB at {mongo.display_uri}: {exc}") from exc
    return client


def get_database() -> Database:
    return get_client()[get_settings().mongo.database]
