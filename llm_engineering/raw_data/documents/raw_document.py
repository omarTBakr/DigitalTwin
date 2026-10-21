from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from llm_engineering.raw_data.documents.provenance import Provenance
from llm_engineering.raw_data.documents.types import Origin, SourceKind


class RawDocument(BaseModel):
    """The single output contract of every extractor."""

    id: str  # "{source}:{native_id}" — stable across runs; Mongo _id
    provider: str  # extractor that produced it ("medium", "github", ...)
    source: SourceKind
    owner_id: str | None = None  # the user whose own writing this is; None = external knowledge
    source_ids: list[str] = Field(default_factory=list)  # registered sources that found it (merged on upsert)
    origin: Origin
    title: str | None = None
    content: str  # markdown
    url: str | None = None  # web URL, or vault-relative path for Obsidian
    author: str
    created_at: datetime | None = None
    updated_at: datetime | None = None
    content_hash: str
    topics: list[str] = Field(default_factory=list)
    provenance: list[Provenance] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
