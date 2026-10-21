from pathlib import Path
from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from llm_engineering.raw_data.documents.types import Origin
from llm_engineering.registry.keys import obsidian_key
from llm_engineering.registry.specs.base import BaseSourceSpec
from llm_engineering.settings.paths import from_root


class TopicRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    glob: str  # fnmatch glob on the vault-relative path
    topic: str


class ObsidianSpec(BaseSourceSpec):
    """One Obsidian vault on this machine."""

    provider: ClassVar[str] = "obsidian"
    owned: ClassVar[bool] = True

    type: Literal["obsidian"]
    vault_path: Path
    include: list[str] = ["*.md"]
    exclude: list[str] = Field(default_factory=list)
    skip_hidden: bool = True
    include_hidden: list[str] = Field(default_factory=list)  # hidden paths to keep anyway, e.g. "x/.src/*"
    min_chars: int = Field(40, ge=0)
    # PDFs (extracted with LangChain PyPDFLoader). Third-party material is external knowledge, not your voice.
    pdf_include: list[str] = Field(default_factory=list)  # e.g. ["images/*.pdf"]; empty = no PDFs
    pdf_origin: Origin = "external"
    pdf_max_mb: float = Field(100, gt=0)
    topic_rules: list[TopicRule] = Field(default_factory=list)

    @field_validator("vault_path")
    @classmethod
    def _anchor(cls, v: Path) -> Path:
        return from_root(v)

    def key(self, user_id: str) -> str:
        return obsidian_key(user_id, self.vault_path)

    def referenced_topics(self) -> set[str]:
        return {r.topic for r in self.topic_rules}
