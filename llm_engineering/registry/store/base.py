from abc import ABC, abstractmethod
from collections.abc import Iterable

from llm_engineering.registry.models.source import Source
from llm_engineering.registry.models.source_state import SourceState
from llm_engineering.registry.models.subscription import Subscription
from llm_engineering.registry.models.user import User


class RegistryStore(ABC):
    """Users, sources and subscriptions. Every storage provider (MongoDB today) implements this.

    Contract: sources are unique by canonical id; `upsert_source` updates the declaration (spec, topics,
    enabled) but never touches `state`; subscriptions are unique per (user, source).
    Implementations raise RegistryError (or other StorageError subclasses), never driver exceptions.
    """

    @abstractmethod
    def setup(self) -> None:
        """Create indexes/tables if missing. Safe to call on every run."""

    @abstractmethod
    def upsert_user(self, user: User) -> None: ...

    @abstractmethod
    def upsert_source(self, source: Source) -> bool:
        """Insert or update a source's declaration. Returns True if it was newly created."""

    @abstractmethod
    def subscribe(self, user_id: str, source_id: str) -> bool:
        """Link a user to a source. Returns True if the subscription is new."""

    @abstractmethod
    def users(self) -> list[User]: ...

    @abstractmethod
    def sources(self, source_ids: Iterable[str] | None = None) -> list[Source]:
        """All sources, or exactly these ids (missing ids are simply absent from the result)."""

    @abstractmethod
    def subscriptions(self, user_id: str | None = None) -> list[Subscription]: ...

    @abstractmethod
    def record_state(self, source_id: str, state: SourceState) -> None:
        """Store the outcome of the latest crawl of a source."""
