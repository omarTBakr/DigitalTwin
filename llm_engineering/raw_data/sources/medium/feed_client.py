import time
from types import TracebackType
from urllib.parse import urlsplit

import feedparser
import httpx

from llm_engineering.exceptions import RateLimitError, SourceUnavailableError
from llm_engineering.raw_data.sources.medium.feed_entry import FeedEntry

MEDIUM = "https://medium.com"
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) DigitalTwinCrawler/0.1"


def feed_url_for_article(url: str) -> str | None:
    """The official RSS feed most likely to contain an article: its author's or its publication's.

    medium.com/@handle/slug-id   -> medium.com/feed/@handle
    medium.com/publication/slug  -> medium.com/feed/publication
    handle.medium.com/slug-id    -> handle.medium.com/feed
    """
    parts = urlsplit(url)
    host = parts.netloc.lower()
    first = next((p for p in parts.path.split("/") if p), "")
    if host in ("medium.com", "www.medium.com"):
        return f"{MEDIUM}/feed/{first}" if first else None
    if host.endswith(".medium.com"):
        return f"https://{host}/feed"
    return None


class MediumFeedClient:
    """Fetches Medium's official RSS feeds politely: a pause between requests, backoff on 429/5xx,
    and each feed fetched at most once per run (cached)."""

    def __init__(self, *, source: str, delay_s: float = 3.0, max_retries: int = 3):
        self.source = source
        self.delay_s = delay_s
        self.max_retries = max_retries
        self._http = httpx.Client(headers={"User-Agent": USER_AGENT}, follow_redirects=True, timeout=20)
        self._cache: dict[str, list[FeedEntry]] = {}
        self._last_request = 0.0

    def __enter__(self) -> "MediumFeedClient":
        return self

    def __exit__(
        self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: TracebackType | None
    ) -> None:
        self._http.close()

    def author_feed(self, handle: str) -> list[FeedEntry]:
        return self.entries(f"{MEDIUM}/feed/{handle}")

    def tag_feed(self, tag: str) -> list[FeedEntry]:
        """The tag's latest posts (previews only; useful for their links)."""
        return self.entries(f"{MEDIUM}/feed/tag/{tag.strip().lower()}")

    def entries(self, feed_url: str) -> list[FeedEntry]:
        if feed_url not in self._cache:
            parsed = feedparser.parse(self._get(feed_url))
            self._cache[feed_url] = [FeedEntry.from_feedparser(e) for e in parsed.entries]
        return self._cache[feed_url]

    def _get(self, url: str) -> str:
        for attempt in range(self.max_retries + 1):
            wait = self.delay_s - (time.monotonic() - self._last_request)
            if wait > 0:
                time.sleep(wait)
            self._last_request = time.monotonic()
            try:
                resp = self._http.get(url)
            except httpx.HTTPError as exc:
                raise SourceUnavailableError(f"{url}: {exc}", source=self.source) from exc
            if resp.status_code == 200:
                return resp.text
            if resp.status_code == 429 or resp.status_code >= 500:
                time.sleep(self.delay_s * 2 ** (attempt + 1))
                continue
            raise SourceUnavailableError(f"{url}: HTTP {resp.status_code}", source=self.source)
        raise RateLimitError(f"{url}: still throttled after {self.max_retries} retries", source=self.source)
