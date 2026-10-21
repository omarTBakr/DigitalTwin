from collections.abc import Iterable

from pydantic import ValidationError
from pymongo import ASCENDING, UpdateOne
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import PyMongoError

from llm_engineering.exceptions import RegistryError, StoreCorruptedError
from llm_engineering.infrastructure.mongo.client import get_database
from llm_engineering.registry.keys import subscription_key
from llm_engineering.registry.models.source import Source
from llm_engineering.registry.models.source_state import SourceState
from llm_engineering.registry.models.subscription import Subscription
from llm_engineering.registry.models.user import User
from llm_engineering.registry.store.base import RegistryStore
from llm_engineering.utils.dates import utc_now

USERS = "users"
SOURCES = "sources"
SUBSCRIPTIONS = "subscriptions"
DECLARATION_FIELDS = ("type", "provider", "spec", "owner_id", "topics", "enabled")  # never `state`


class MongoRegistryStore(RegistryStore):
    """`users`, `sources` and `subscriptions` collections; `_id` is the user id / canonical source key."""

    def __init__(self, database: Database | None = None):
        db = database if database is not None else get_database()
        self.users_col: Collection = db[USERS]
        self.sources_col: Collection = db[SOURCES]
        self.subscriptions_col: Collection = db[SUBSCRIPTIONS]

    def setup(self) -> None:
        try:
            self.sources_col.create_index([("provider", ASCENDING)])
            self.sources_col.create_index([("owner_id", ASCENDING)])
            self.subscriptions_col.create_index([("user_id", ASCENDING), ("source_id", ASCENDING)], unique=True)
            self.subscriptions_col.create_index([("source_id", ASCENDING)])
        except PyMongoError as exc:
            raise RegistryError(f"cannot create registry indexes: {exc}") from exc

    def upsert_user(self, user: User) -> None:
        data = user.model_dump(mode="python")
        self._run(lambda: self.users_col.update_one({"_id": data.pop("id")}, {"$set": data}, upsert=True))

    def upsert_source(self, source: Source) -> bool:
        result = self._run(lambda: self.sources_col.bulk_write([self.source_upsert_op(source)]))
        return result.upserted_count == 1

    @staticmethod
    def source_upsert_op(source: Source) -> UpdateOne:
        """Declaration fields are overwritten; `state` is only initialised on insert, never clobbered."""
        data = source.model_dump(mode="python")
        return UpdateOne(
            {"_id": source.id},
            {"$set": {f: data[f] for f in DECLARATION_FIELDS}, "$setOnInsert": {"state": data["state"]}},
            upsert=True,
        )

    def subscribe(self, user_id: str, source_id: str) -> bool:
        result = self._run(
            lambda: self.subscriptions_col.update_one(
                {"_id": subscription_key(user_id, source_id)},
                {"$setOnInsert": {"user_id": user_id, "source_id": source_id, "created_at": utc_now()}},
                upsert=True,
            )
        )
        return result.upserted_id is not None

    def users(self) -> list[User]:
        return [self._model(User, self._with_id(raw), USERS) for raw in self._run(lambda: list(self.users_col.find()))]

    def sources(self, source_ids: Iterable[str] | None = None) -> list[Source]:
        query = {} if source_ids is None else {"_id": {"$in": list(source_ids)}}
        raws = self._run(lambda: list(self.sources_col.find(query)))
        return [self._model(Source, self._with_id(raw), SOURCES) for raw in raws]

    def subscriptions(self, user_id: str | None = None) -> list[Subscription]:
        query = {"user_id": user_id} if user_id else {}
        raws = self._run(lambda: list(self.subscriptions_col.find(query)))
        return [self._model(Subscription, {k: v for k, v in raw.items() if k != "_id"}, SUBSCRIPTIONS) for raw in raws]

    def record_state(self, source_id: str, state: SourceState) -> None:
        self._run(lambda: self.sources_col.update_one({"_id": source_id}, {"$set": {"state": state.model_dump()}}))

    @staticmethod
    def _run(operation):
        try:
            return operation()
        except PyMongoError as exc:
            raise RegistryError(f"registry operation failed: {exc}") from exc

    @staticmethod
    def _with_id(raw: dict) -> dict:
        """Mongo's `_id` becomes the model's `id` (models reject unknown keys like `_id`)."""
        return {"id": raw["_id"], **{k: v for k, v in raw.items() if k != "_id"}}

    @staticmethod
    def _model(model, raw: dict, collection: str):
        try:
            return model.model_validate(raw)
        except ValidationError as exc:
            raise StoreCorruptedError(str(exc), location=f"{collection}/{raw.get('_id')}") from exc
