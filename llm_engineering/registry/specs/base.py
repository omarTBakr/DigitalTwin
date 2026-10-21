from abc import ABC, abstractmethod
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, ValidationInfo, model_validator

from llm_engineering.settings.paths import TOPICS_FILE


class BaseSourceSpec(BaseModel, ABC):
    """What a user declares to subscribe to one source (YAML today, a UI form later).

    Subclasses set `provider` (which extractor crawls it) and `owned` (True = the user's own writing:
    documents get owner_id; False = shared external knowledge), and implement `key()`.
    """

    model_config = ConfigDict(extra="forbid")  # catches typos in YAML keys / form fields

    provider: ClassVar[str]
    owned: ClassVar[bool]

    enabled: bool = True

    @abstractmethod
    def key(self, user_id: str) -> str:
        """Canonical source id. Equal for equal sources, so declaring one twice never duplicates it."""

    def declared_topics(self) -> list[str]:
        """Topics stored on the source record (what it was subscribed for)."""
        return []

    def referenced_topics(self) -> set[str]:
        """Every topic key the spec mentions; checked against topics.yaml at load time."""
        return set(self.declared_topics())

    @model_validator(mode="after")
    def _check_topics(self, info: ValidationInfo):
        known = (info.context or {}).get("topics")
        if known is None:
            return self
        unknown = self.referenced_topics() - set(known)
        if unknown:
            raise ValueError(f"unknown topics {sorted(unknown)}; define them in {TOPICS_FILE}")
        return self
