from typing import Any

from pydantic import BaseModel, Field


class SourceHealth(BaseModel):
    """Result of BaseExtractor.health_check()."""

    source: str
    ok: bool
    summary: str
    details: dict[str, Any] = Field(default_factory=dict)
