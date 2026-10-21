from typing import ClassVar, Literal

from pydantic import Field, field_validator

from llm_engineering.registry.keys import medium_author_key
from llm_engineering.registry.specs.base import BaseSourceSpec
from llm_engineering.registry.specs.medium_tag import MEDIUM


class MediumAuthorSpec(BaseSourceSpec):
    """Latest articles of one Medium author."""

    provider: ClassVar[str] = "medium"
    owned: ClassVar[bool] = False

    type: Literal["medium_author"]
    handle: str  # "@name"
    topics: list[str] = Field(min_length=1)  # what we follow this author for (filters their articles)

    @field_validator("handle")
    @classmethod
    def _at_prefix(cls, v: str) -> str:
        v = v.strip()
        return v if v.startswith("@") else f"@{v}"

    def key(self, user_id: str) -> str:
        return medium_author_key(self.handle)

    def declared_topics(self) -> list[str]:
        return self.topics

    @property
    def listing_url(self) -> str:
        return f"{MEDIUM}/{self.handle}"
