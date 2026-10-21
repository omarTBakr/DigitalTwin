from typing import ClassVar, Literal

from pydantic import Field, HttpUrl

from llm_engineering.raw_data.documents.types import Origin
from llm_engineering.registry.keys import article_key
from llm_engineering.registry.specs.base import BaseSourceSpec


class ArticleSpec(BaseSourceSpec):
    """One web article (blog post, docs page), crawled with CustomArticleCrawler."""

    provider: ClassVar[str] = "articles"
    owned: ClassVar[bool] = False

    type: Literal["article"]
    url: HttpUrl
    topics: list[str] = Field(default_factory=list)
    origin: Origin = "external"  # "self" for an article the user wrote on their own site

    def key(self, user_id: str) -> str:
        return article_key(str(self.url))

    def declared_topics(self) -> list[str]:
        return self.topics
