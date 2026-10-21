from collections import Counter
from collections.abc import Iterable, Iterator

from pydantic import ValidationError
from pymongo import ASCENDING, UpdateOne
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import PyMongoError

from llm_engineering.exceptions import StorageError, StoreCorruptedError
from llm_engineering.infrastructure.mongo.client import get_database
from llm_engineering.raw_data.documents.raw_document import RawDocument
from llm_engineering.raw_data.store.base import RawDataStore
from llm_engineering.raw_data.store.upsert_stats import UpsertStats

COLLECTION = "raw_documents"
PROVENANCE_KEPT = 50  # last N sightings per document


class MongoRawDataStore(RawDataStore):
    """One collection for all sources, `_id` = RawDocument.id."""

    def __init__(self, database: Database | None = None):
        db = database if database is not None else get_database()
        self.collection: Collection = db[COLLECTION]

    def setup(self) -> None:
        try:
            for field in ("provider", "owner_id", "source_ids", "topics", "origin"):
                self.collection.create_index([(field, ASCENDING)])
        except PyMongoError as exc:
            raise StorageError(f"cannot create indexes on {COLLECTION}: {exc}") from exc

    def upsert_many(self, docs: Iterable[RawDocument]) -> UpsertStats:
        ops = [self._upsert_op(doc) for doc in docs]
        if not ops:
            return UpsertStats()
        try:
            result = self.collection.bulk_write(ops, ordered=False)
        except PyMongoError as exc:
            raise StorageError(f"bulk upsert into {COLLECTION} failed: {exc}") from exc
        return UpsertStats(inserted=result.upserted_count, matched=result.matched_count)

    @staticmethod
    def _upsert_op(doc: RawDocument) -> UpdateOne:
        data = doc.model_dump(mode="python")
        fields = {k: v for k, v in data.items() if k not in ("id", "topics", "source_ids", "provenance")}
        return UpdateOne(
            {"_id": doc.id},
            {
                "$set": fields,
                "$addToSet": {"topics": {"$each": data["topics"]}, "source_ids": {"$each": data["source_ids"]}},
                "$push": {"provenance": {"$each": data["provenance"], "$slice": -PROVENANCE_KEPT}},
            },
            upsert=True,
        )

    def find(self, provider: str | None = None, owner_id: str | None = None) -> Iterator[RawDocument]:
        query = self._filter(provider) | ({"owner_id": owner_id} if owner_id else {})
        try:
            for raw in self.collection.find(query):
                yield self._to_document(raw)
        except PyMongoError as exc:
            raise StorageError(f"cannot read {COLLECTION}: {exc}") from exc

    def topics_by_id(self, provider: str) -> dict[str, set[str]]:
        try:
            cursor = self.collection.find(self._filter(provider), {"topics": 1})
            return {raw["_id"]: set(raw.get("topics", [])) for raw in cursor}
        except PyMongoError as exc:
            raise StorageError(f"cannot read {COLLECTION}: {exc}") from exc

    def counts_by_topic(self, provider: str) -> Counter[str]:
        pipeline = [
            {"$match": self._filter(provider)},
            {"$unwind": "$topics"},
            {"$group": {"_id": "$topics", "n": {"$sum": 1}}},
        ]
        try:
            return Counter({row["_id"]: row["n"] for row in self.collection.aggregate(pipeline)})
        except PyMongoError as exc:
            raise StorageError(f"cannot aggregate {COLLECTION}: {exc}") from exc

    def count(self, provider: str | None = None) -> int:
        try:
            return self.collection.count_documents(self._filter(provider))
        except PyMongoError as exc:
            raise StorageError(f"cannot count {COLLECTION}: {exc}") from exc

    @staticmethod
    def _filter(provider: str | None) -> dict:
        return {"provider": provider} if provider else {}

    @staticmethod
    def _to_document(raw: dict) -> RawDocument:
        try:
            return RawDocument.model_validate({**raw, "id": raw["_id"]})
        except (ValidationError, KeyError) as exc:
            raise StoreCorruptedError(str(exc), location=f"{COLLECTION}/{raw.get('_id')}") from exc
