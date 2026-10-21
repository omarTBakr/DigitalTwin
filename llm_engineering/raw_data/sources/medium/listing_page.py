import re
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

from llm_engineering.infrastructure.web.browser import Browser
from llm_engineering.registry.specs.medium_tag import MEDIUM

# Medium article URLs end in "-<hex id>", e.g. /@author/my-post-1a2b3c4d5e6f
ARTICLE_PATH = re.compile(r"-([0-9a-f]{8,12})$")
NON_ARTICLE_PREFIXES = ("/tag/", "/m/", "/plans", "/me/", "/search", "/membership")


def article_id(url: str) -> str | None:
    match = ARTICLE_PATH.search(urlsplit(url).path.rstrip("/"))
    return match.group(1) if match else None


def article_links(html: str) -> list[str]:
    """Article URLs in page order, deduped, without query strings."""
    soup = BeautifulSoup(html, "html.parser")
    seen: set[str] = set()
    links: list[str] = []
    for a in soup.find_all("a", href=True):
        parts = urlsplit(urljoin(MEDIUM, a["href"]))
        if not parts.netloc.endswith("medium.com") or parts.path.startswith(NON_ARTICLE_PREFIXES):
            continue
        url = f"{parts.scheme}://{parts.netloc}{parts.path.rstrip('/')}"
        if article_id(url) and url not in seen:
            seen.add(url)
            links.append(url)
    return links


class MediumListingPage:
    """A tag or author page: scroll until enough article links are visible."""

    def __init__(self, browser: Browser, *, scroll_pause_s: float, max_scrolls: int):
        self.browser = browser
        self.scroll_pause_s = scroll_pause_s
        self.max_scrolls = max_scrolls

    def collect(self, url: str, limit: int) -> list[str]:
        links = article_links(self.browser.open(url))
        for _ in range(self.max_scrolls):
            if len(links) >= limit:
                break
            grew = self.browser.scroll_to_bottom(self.scroll_pause_s)
            links = article_links(self.browser.page_source)
            if not grew:
                break
        return links[:limit]
