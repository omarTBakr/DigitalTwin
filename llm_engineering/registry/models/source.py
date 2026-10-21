from functools import cached_property
from typing import Any

from pydantic import BaseModel, Field

from llm_engineering.registry.models.source_state import SourceState
from llm_engineering.registry.specs.registry import SourceSpec, source_spec_adapter


class Source(BaseModel):
    """A registered source: stored once per canonical key, however many users subscribe to it."""

    id: str  # canonical key, e.g. "medium:tag:rag" (Mongo _id)
    type: str  # spec type, e.g. "medium_tag"
    provider: str  # which extractor crawls it, e.g. "medium"
    spec: dict[str, Any]  # the declared spec, JSON-ready
    owner_id: str | None = None  # set for the user's own writing (github, obsidian, linkedin)
    topics: list[str] = Field(default_factory=list)
    enabled: bool = True
    state: SourceState = Field(default_factory=SourceState)

    @classmethod
    def from_spec(cls, spec: SourceSpec, user_id: str) -> "Source":
        return cls(
            id=spec.key(user_id),
            type=spec.type,
            provider=spec.provider,
            spec=spec.model_dump(mode="json"),
            owner_id=user_id if spec.owned else None,
            topics=spec.declared_topics(),
            enabled=spec.enabled,
        )

    @cached_property
    def typed_spec(self) -> SourceSpec:
        """The spec as its Pydantic model (GitHubSpec, MediumTagSpec, ...)."""
        return source_spec_adapter.validate_python(self.spec)
