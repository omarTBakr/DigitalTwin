from pydantic import BaseModel, ConfigDict, Field


class Topic(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: str
    medium_tags: list[str] = Field(default_factory=list)
    obsidian_tags: list[str] = Field(default_factory=list)


class TopicsFile(BaseModel):
    """Shape of configs/topics.yaml."""

    model_config = ConfigDict(extra="forbid")

    topics: dict[str, Topic]
