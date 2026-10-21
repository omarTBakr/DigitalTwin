"""Export rows/files -> LinkedInItem. No I/O here; the extractor turns items into documents."""

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup

from llm_engineering.raw_data.documents.types import SourceKind
from llm_engineering.utils.dates import parse_iso_datetime
from llm_engineering.utils.hashing import short_id
from llm_engineering.utils.text import html_to_markdown

HASHTAG = re.compile(r"#(\w+)")
DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")


@dataclass
class LinkedInItem:
    kind: SourceKind
    native_id: str
    text: str
    title: str | None = None
    url: str | None = None
    created_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def hashtags(self) -> list[str]:
        return HASHTAG.findall(self.text)


def parse_post(row: dict[str, str]) -> LinkedInItem:
    """A row of Shares.csv: Date, ShareLink, ShareCommentary, SharedUrl, MediaUrl, Visibility."""
    text = (row.get("ShareCommentary") or "").strip()
    link = row.get("ShareLink") or ""
    return LinkedInItem(
        kind="linkedin_post",
        native_id=short_id(link or text),
        text=text,
        url=link or None,
        created_at=parse_iso_datetime(row.get("Date")),
        metadata={"shared_url": row.get("SharedUrl"), "visibility": row.get("Visibility")},
    )


def parse_comment(row: dict[str, str]) -> LinkedInItem:
    """A row of Comments.csv: Date, Link, Message."""
    text = (row.get("Message") or "").strip()
    link = row.get("Link") or ""
    return LinkedInItem(
        kind="linkedin_comment",
        native_id=short_id(link, row.get("Date") or "", text),
        text=text,
        url=link or None,
        created_at=parse_iso_datetime(row.get("Date")),
    )


def parse_article(html: str, path: Path) -> LinkedInItem:
    """An exported article: Articles/**/<date>-<title>.html."""
    soup = BeautifulSoup(html, "html.parser")
    heading = soup.find("h1") or soup.find("title")
    date = DATE_PREFIX.match(path.name)
    return LinkedInItem(
        kind="linkedin_article",
        native_id=short_id(path.name),
        text=html_to_markdown(soup.body or soup),
        title=heading.get_text(strip=True) if heading else path.stem,
        created_at=parse_iso_datetime(date.group(1)) if date else None,
        metadata={"file": path.name},
    )
