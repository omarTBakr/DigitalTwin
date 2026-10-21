from dataclasses import dataclass, field
from typing import Any


@dataclass
class CrawledArticle:
    """A web article reduced to text by a generic crawler."""

    url: str
    title: str | None
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)  # description, language, crawler
