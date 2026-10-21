from dataclasses import dataclass, field
from datetime import datetime
from urllib.parse import urlsplit

from bs4 import BeautifulSoup

from llm_engineering.exceptions import ParseError
from llm_engineering.infrastructure.web.browser import Browser
from llm_engineering.utils.dates import parse_iso_datetime
from llm_engineering.utils.text import html_to_markdown

MEMBER_ONLY_MARKER = "Member-only story"


@dataclass
class MediumArticle:
    url: str
    title: str | None
    author: str | None
    published_at: datetime | None
    content: str  # markdown
    tags: list[str] = field(default_factory=list)
    member_only: bool = False


def _meta(soup: BeautifulSoup, **attrs: str) -> str | None:
    tag = soup.find("meta", attrs=attrs)
    return tag.get("content") if tag else None


def parse_article(html: str, url: str) -> MediumArticle:
    """Article HTML -> MediumArticle. Relies on stable signals: <article>, og/article meta, /tag/ links."""
    soup = BeautifulSoup(html, "html.parser")
    body = soup.find("article")
    if body is None:
        raise ParseError("no <article> element", source="medium", item=url)

    for junk in body.find_all(["script", "style", "button", "svg", "noscript"]):
        junk.decompose()
    tags = []
    for a in soup.find_all("a", href=True):
        path = urlsplit(a["href"]).path
        if path.startswith("/tag/"):
            slug = path.removeprefix("/tag/").split("/")[0]
            if slug and slug not in tags:
                tags.append(slug)

    h1 = body.find("h1")
    return MediumArticle(
        url=url,
        title=_meta(soup, property="og:title") or (h1.get_text(strip=True) if h1 else None),
        author=_meta(soup, name="author"),
        published_at=parse_iso_datetime(_meta(soup, property="article:published_time")),
        content=html_to_markdown(body),
        tags=tags,
        member_only=MEMBER_ONLY_MARKER in soup.get_text(" ", strip=True)[:5000],
    )


class MediumArticlePage:
    """Loads one article in the browser and parses it."""

    def __init__(self, browser: Browser):
        self.browser = browser

    def load(self, url: str) -> MediumArticle:
        return parse_article(self.browser.open(url), url)
