import logging
import os
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import frontmatter

from llm_engineering.exceptions import ParseError
from llm_engineering.utils.globs import matches_any

log = logging.getLogger(__name__)


@dataclass
class Note:
    path: Path  # vault-relative
    metadata: dict  # frontmatter
    body: str
    modified_at: datetime

    @property
    def rel(self) -> str:
        return self.path.as_posix()


class ObsidianVault:
    """Walks a vault and reads notes (frontmatter + body)."""

    def __init__(
        self,
        root: Path,
        *,
        include: list[str],
        exclude: list[str],
        skip_hidden: bool = True,
        source: str = "obsidian",
    ):
        self.root = root
        self.include = include
        self.exclude = exclude
        self.skip_hidden = skip_hidden
        self.source = source

    def exists(self) -> bool:
        return self.root.is_dir()

    def note_paths(self) -> Iterator[Path]:
        """Vault-relative paths that pass include/exclude/skip_hidden."""
        for dirpath, dirnames, filenames in os.walk(self.root):
            if self.skip_hidden:
                dirnames[:] = [d for d in dirnames if not d.startswith(".")]
            for name in filenames:
                if self.skip_hidden and name.startswith("."):
                    continue
                rel = (Path(dirpath) / name).relative_to(self.root)
                rel_str = rel.as_posix()
                if matches_any(rel_str, self.include) and not matches_any(rel_str, self.exclude):
                    yield rel

    def read(self, rel: Path) -> Note:
        path = self.root / rel
        try:
            raw = path.read_text(encoding="utf-8", errors="replace")
            modified_at = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
        except OSError as exc:
            raise ParseError(str(exc), source=self.source, item=rel.as_posix()) from exc
        try:
            post = frontmatter.loads(raw)
            metadata, body = dict(post.metadata), post.content
        except Exception as exc:  # malformed YAML frontmatter shouldn't drop the note
            log.debug("%s: bad frontmatter (%s), using raw text", rel, exc)
            metadata, body = {}, raw
        return Note(path=rel, metadata=metadata, body=body, modified_at=modified_at)
