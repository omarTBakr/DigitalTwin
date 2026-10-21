from pydantic import BaseModel, ConfigDict, Field


class User(BaseModel):
    """A person the twin is built for. Their own writing links to them via RawDocument.owner_id."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]*$")  # stable, url-safe; part of some source keys
    name: str  # used as the author of the user's own documents
    handles: dict[str, str] = Field(default_factory=dict)  # platform -> handle, e.g. {"github": "omarTBakr"}
