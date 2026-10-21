from pydantic import BaseModel, model_validator

from llm_engineering.registry.models.user import User
from llm_engineering.registry.specs.registry import SourceSpec


class UserDeclaration(BaseModel):
    """A user and the sources they want ingested — from YAML today, from a UI later."""

    user: User
    sources: list[SourceSpec]

    @model_validator(mode="after")
    def _no_duplicate_sources(self):
        keys = [spec.key(self.user.id) for spec in self.sources]
        dupes = sorted({k for k in keys if keys.count(k) > 1})
        if dupes:
            raise ValueError(f"user {self.user.id!r} declares these sources more than once: {dupes}")
        return self
