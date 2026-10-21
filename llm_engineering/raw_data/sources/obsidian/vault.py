import logging
import os
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import yaml

from llm_engineering.exceptions import SourceUnavailableError
from llm_engineering.raw_data.sources.obsidian.note_loader import (
    CodeAwareObsidianLoader,
)
from llm_engineering.utils.globs import has_hidden_part, matches_any

log = logging.getLogger(__name__)

# keys ObsidianLoader adds about the file itself; everything else in its metadata is frontmatter/dataview
FILE_KEYS = {"source", "path", "created", "last_modified", "last_accessed", "tags"}


@dataclass
class Note:
    path: Path  # vault-relative
    body: str  # markdown without frontmatter
    metadata: dict  # frontmatter + dataview fields (values stringified by ObsidianLoader)
    tags: list[str] = field(default_factory=list)
    modified_at: datetime | None = None

    @property
    def rel(self) -> str:
        return self.path.as_posix()


class ObsidianVault:
    """A vault on disk: notes via LangChain's ObsidianLoader, PDFs by glob, both filtered by our rules."""

    def __init__(
        self,
        root: Path,
        *,
        include: list[str],
        exclude: list[str],
        skip_hidden: bool = True,
        include_hidden: list[str] | None = None,
        source: str = "obsidian",
    ):
        self.root = root
        self.include = include
        self.exclude = exclude
        self.skip_hidden = skip_hidden
        self.include_hidden = include_hidden or []
        self.source = source

    def exists(self) -> bool:
        return self.root.is_dir()

    def wanted(self, rel: str, include: list[str]) -> bool:
        """include/exclude globs; hidden paths only when allowed by `include_hidden`."""
        if self.skip_hidden and has_hidden_part(rel) and not matches_any(rel, self.include_hidden):
            return False
        return matches_any(rel, include) and not matches_any(rel, self.exclude)

    def notes(self) -> Iterator[Note]:
        """Every wanted markdown note. ObsidianLoader reads the whole vault in one pass, so a file it
        can't read stops the vault (SourceUnavailableError) instead of skipping one note."""
        try:
            for doc in CodeAwareObsidianLoader(str(self.root)).lazy_load():
                rel = Path(doc.metadata["path"]).relative_to(self.root)
                if not self.wanted(rel.as_posix(), self.include):
                    continue
                meta = doc.metadata
                frontmatter = {k: v for k, v in meta.items() if k not in FILE_KEYS}
                if isinstance(meta.get("created"), str):  # a frontmatter `created:` overrides the file ctime
                    frontmatter["created"] = meta["created"]
                yield Note(
                    path=rel,
                    body=doc.page_content,
                    metadata=frontmatter,
                    tags=[t for t in str(meta.get("tags", "")).split(",") if t],
                    modified_at=datetime.fromtimestamp(meta["last_modified"], tz=UTC),
                )
        except (OSError, UnicodeDecodeError, ValueError, TypeError, yaml.YAMLError) as exc:
            raise SourceUnavailableError(f"ObsidianLoader could not read the vault: {exc}", source=self.source) from exc

    def pdf_paths(self, patterns: list[str]) -> Iterator[Path]:
        """Vault-relative PDFs matching `patterns` (and the vault's exclude/hidden rules)."""
        if not patterns:
            return
        for dirpath, _, filenames in os.walk(self.root):
            for name in filenames:
                if name.lower().endswith(".pdf"):
                    rel = (Path(dirpath) / name).relative_to(self.root)
                    if self.wanted(rel.as_posix(), patterns):
                        yield rel
