from pathlib import Path
from typing import ClassVar, Literal

from pydantic import Field, field_validator

from llm_engineering.registry.keys import linkedin_key
from llm_engineering.registry.specs.base import BaseSourceSpec
from llm_engineering.settings.paths import from_root


class LinkedInExportSpec(BaseSourceSpec):
    """The user's official LinkedIn data export, unzipped into `export_dir`."""

    provider: ClassVar[str] = "linkedin"
    owned: ClassVar[bool] = True

    type: Literal["linkedin_export"]
    export_dir: Path  # one folder per user, e.g. data/exports/linkedin/<user_id>
    include: list[Literal["posts", "articles", "comments"]] = ["posts", "articles", "comments"]
    min_chars: int = Field(40, ge=0)

    @field_validator("export_dir")
    @classmethod
    def _anchor(cls, v: Path) -> Path:
        return from_root(v)

    def key(self, user_id: str) -> str:
        return linkedin_key(user_id)
