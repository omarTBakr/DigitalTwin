from typing import ClassVar, Literal

from pydantic import Field

from llm_engineering.registry.keys import medium_tag_key, slug
from llm_engineering.registry.specs.base import BaseSourceSpec

MEDIUM = "https://medium.com"


class MediumTagSpec(BaseSourceSpec):
    """Top ("recommended") Medium articles for one tag."""

    provider: ClassVar[str] = "medium"
    owned: ClassVar[bool] = False

    type: Literal["medium_tag"]
    tag: str
    topics: list[str] = Field(min_length=1)  # every article found here gets these topics

    def key(self, user_id: str) -> str:
        return medium_tag_key(self.tag)

    def declared_topics(self) -> list[str]:
        return self.topics

    @property
    def listing_url(self) -> str:
        return f"{MEDIUM}/tag/{slug(self.tag)}/recommended"
