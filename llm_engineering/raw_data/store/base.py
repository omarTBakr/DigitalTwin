from abc import ABC, abstractmethod
from collections import Counter
from collections.abc import Iterable, Iterator

from llm_engineering.raw_data.documents.raw_document import RawDocument
from llm_engineering.raw_data.store.upsert_stats import UpsertStats


class RawDataStore(ABC):
    """Where raw documents live. Every storage provider (MongoDB today) implements this.

    Upsert contract (all implementations): a document is keyed by `RawDocument.id`; re-saving it
    overwrites the content fields with the latest crawl, unions `topics` and `source_ids`, and appends
    `provenance`.
    Implementations raise StorageError subclasses, never driver-specific exceptions.
    """

    @abstractmethod
    def setup(self) -> None:
        """Create indexes/tables if missing. Safe to call on every run."""

    @abstractmethod
    def upsert_many(self, docs: Iterable[RawDocument]) -> UpsertStats:
        """Insert new documents and merge existing ones (see class docstring)."""

    @abstractmethod
    def find(self, provider: str | None = None, owner_id: str | None = None) -> Iterator[RawDocument]:
        """Stored documents, optionally only one provider's and/or one user's own writing."""

    @abstractmethod
    def topics_by_id(self, provider: str) -> dict[str, set[str]]:
        """Document id -> stored topics, for one provider (used to enforce per-topic caps across runs)."""

    @abstractmethod
    def counts_by_topic(self, provider: str) -> Counter[str]:
        """Number of stored documents per topic, for one provider."""

    @abstractmethod
    def count(self, provider: str | None = None) -> int:
        """Number of stored documents, optionally for one provider."""
