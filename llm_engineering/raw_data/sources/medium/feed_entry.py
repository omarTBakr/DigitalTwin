from dataclasses import dataclass, field
from datetime import UTC, datetime

from bs4 import BeautifulSoup

from llm_engineering.utils.text import html_to_markdown


@dataclass
class FeedEntry:
    """One post from a Medium RSS feed (author or publication)."""

    article_id: str  # Medium's post id, the hex suffix of the URL ("df494ebc2c78")
    url: str
    title: str | None
    author: str | None
    published_at: datetime | None
    tags: list[str] = field(default_factory=list)
    content: str = ""  # markdown; empty when the feed only carries a preview
    full_text: bool = False  # False for member-only posts (RSS gives a snippet)

    @classmethod
    def from_feedparser(cls, entry) -> "FeedEntry":
        content = entry.get("content")
        html = content[0].get("value", "") if content else ""
        published = entry.get("published_parsed")
        return cls(
            article_id=(entry.get("id") or entry.get("link", "")).rstrip("/").rsplit("/", 1)[-1],
            url=entry.get("link", "").split("?")[0],
            title=entry.get("title"),
            author=entry.get("author"),
            published_at=datetime(*published[:6], tzinfo=UTC) if published else None,
            tags=[t.get("term", "") for t in entry.get("tags", []) if t.get("term")],
            content=_clean(html) if html else "",
            full_text=bool(html),
        )


def _clean(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for img in soup.find_all("img"):
        if "/_/stat" in (img.get("src") or ""):  # Medium's tracking pixel
            img.decompose()
    return html_to_markdown(soup)
