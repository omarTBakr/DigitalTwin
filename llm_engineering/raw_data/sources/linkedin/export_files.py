import csv
from collections.abc import Iterator
from pathlib import Path

from llm_engineering.exceptions import ParseError

SHARES_CSV = "Shares.csv"
COMMENTS_CSV = "Comments.csv"


class LinkedInExport:
    """Locates and reads the files of an unzipped LinkedIn data export (often nested one folder deep)."""

    def __init__(self, root: Path, *, source: str):
        self.root = root
        self.source = source

    def exists(self) -> bool:
        return self.root.is_dir() and any(self.root.iterdir())

    def find(self, name: str) -> Path | None:
        return next(iter(sorted(self.root.rglob(name))), None)

    def article_files(self) -> list[Path]:
        return [p for p in sorted(self.root.rglob("*.html")) if "article" in str(p.relative_to(self.root)).lower()]

    def read_csv(self, path: Path) -> Iterator[dict[str, str]]:
        try:
            with path.open(encoding="utf-8-sig", newline="") as f:
                yield from csv.DictReader(f)
        except (OSError, csv.Error, UnicodeDecodeError) as exc:
            raise ParseError(str(exc), source=self.source, item=path.name) from exc

    def read_text(self, path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise ParseError(str(exc), source=self.source, item=path.name) from exc
