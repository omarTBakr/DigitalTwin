from collections.abc import Iterator
from contextlib import contextmanager
from typing import ClassVar

from llm_engineering.exceptions import (
    AccessBlockedError,
    ParseError,
    SourceError,
    SourceUnavailableError,
)
from llm_engineering.infrastructure.web.browser import Browser
from llm_engineering.raw_data.crawlers.crawled_article import CrawledArticle
from llm_engineering.raw_data.crawlers.custom_article_crawler import (
    CustomArticleCrawler,
)
from llm_engineering.raw_data.documents.raw_document import RawDocument
from llm_engineering.raw_data.sources.base.extractor import BaseExtractor
from llm_engineering.raw_data.sources.base.health import SourceHealth
from llm_engineering.raw_data.sources.medium.article_page import (
    MEMBER_ONLY_MARKER,
    MediumArticle,
    MediumArticlePage,
)
from llm_engineering.raw_data.sources.medium.listing_page import (
    MediumListingPage,
    article_id,
)
from llm_engineering.raw_data.sources.medium.settings import MediumSettings
from llm_engineering.registry.models.source import Source
from llm_engineering.registry.specs.medium_author import MediumAuthorSpec
from llm_engineering.registry.specs.medium_tag import MediumTagSpec

SELENIUM = "selenium"
FALLBACK = "custom_fallback"


class MediumExtractor(BaseExtractor[MediumSettings]):
    """Medium tag and author sources, browsed with Selenium (one browser for the whole run).

    Each source: open its listing page (tag "recommended" or author page), collect article links,
    open each article; CustomArticleCrawler retries a failed article when `use_fallback`.
    Topics: tag sources give their topics plus the article's mapped tags; author sources keep only the
    article's mapped tags that the author is followed for (all of them if none map).
    Per-topic caps hold across runs (existing topics come from the store via the context).
    """

    provider: ClassVar[str] = "medium"

    def _browser(self) -> Browser:
        s = self.settings
        return Browser(
            source=self.provider,
            headless=s.headless,
            page_load_timeout_s=s.page_load_timeout_s,
            binary_path=s.browser_binary,
            user_data_dir=s.user_data_dir,
            profile_directory=s.profile_directory,
            delay_s=(s.action_delay_min_s, s.action_delay_max_s),
        )

    @contextmanager
    def session(self):
        s = self.settings
        self.counts = self.context.topic_counts()
        self.known = {doc_id: set(topics) for doc_id, topics in self.context.existing_topics.items()}
        with self._browser() as browser:
            self.browser = browser
            self.listing = MediumListingPage(browser, max_scrolls=s.max_scrolls)
            self.articles = MediumArticlePage(browser)
            yield

    def extract_source(self, source: Source) -> Iterator[RawDocument]:
        spec: MediumTagSpec | MediumAuthorSpec = source.typed_spec
        missing = max(self.settings.limit_per_topic - self.counts[t] for t in spec.topics)
        if missing <= 0:
            self.record_skipped(spec.listing_url, f"topics {spec.topics} already at cap")
            return
        try:
            urls = self.listing.collect(spec.listing_url, limit=missing * 2)  # extra: some get skipped
        except AccessBlockedError:
            raise
        except SourceUnavailableError as exc:
            self.record_failed(spec.listing_url, f"listing page: {exc}")
            raise
        self.log.info("%s: %d article links", spec.listing_url, len(urls))
        yield from self._articles(source, spec, urls)

    def _articles(self, source: Source, spec: MediumTagSpec | MediumAuthorSpec, urls: list[str]) -> Iterator[RawDocument]:
        limit = self.settings.limit_per_topic
        for rank, url in enumerate(urls, start=1):
            if all(self.counts[t] >= limit for t in spec.topics):
                return
            doc_id = f"medium:{article_id(url)}"
            already = self.known.get(doc_id, set())
            if set(spec.topics) <= already:
                self.record_skipped(url, "already stored for these topics")
                continue  # don't re-download

            loaded = self._load(url)
            if loaded is None:
                continue
            article, crawler = loaded
            if self.settings.skip_member_only and article.member_only:
                self.record_skipped(url, "member-only story")
                continue

            topics = self.article_topics(spec, article)
            accepted = {t for t in topics - already if self.counts[t] < limit}
            if not accepted:
                self.record_skipped(url, f"topics {sorted(topics - already)} already at cap")
                continue
            for t in accepted:
                self.counts[t] += 1
            self.known[doc_id] = already | accepted
            yield self._document(source, doc_id, article, self.known[doc_id], spec.listing_url, rank, crawler)

    def article_topics(self, spec: MediumTagSpec | MediumAuthorSpec, article: MediumArticle) -> set[str]:
        mapped = self.context.matcher.from_tags(article.tags)
        if isinstance(spec, MediumTagSpec):
            return set(spec.topics) | mapped
        return (mapped & set(spec.topics)) or set(spec.topics)

    def _load(self, url: str) -> tuple[MediumArticle, str] | None:
        """Selenium first, then the generic crawler. None = skip this article."""
        try:
            return self.articles.load(url), SELENIUM
        except (ParseError, SourceUnavailableError) as exc:
            if not self.settings.use_fallback:
                self.record_failed(url, str(exc))
                if isinstance(exc, AccessBlockedError):
                    raise
                self.log.warning("%s", exc)
                return None
            self.log.info("%s; trying %s", exc, FALLBACK)
            try:
                crawled = CustomArticleCrawler(source=self.provider).crawl(url)
            except (ParseError, SourceUnavailableError) as fallback_exc:
                self.record_failed(url, f"{exc}; fallback: {fallback_exc}")
                if isinstance(exc, AccessBlockedError):
                    raise exc from fallback_exc
                self.log.warning("%s (fallback also failed: %s)", exc, fallback_exc)
                return None
            return self.from_crawled(crawled), FALLBACK

    @staticmethod
    def from_crawled(crawled: CrawledArticle) -> MediumArticle:
        """CustomArticleCrawler output -> MediumArticle (no tags or author meta in plain text)."""
        return MediumArticle(
            url=crawled.url,
            title=crawled.title,
            author=None,
            published_at=None,
            content=crawled.content,
            tags=[],
            member_only=MEMBER_ONLY_MARKER in crawled.content[:5000],
        )

    def _document(
        self, source: Source, doc_id: str, article: MediumArticle, topics: set[str], query: str, rank: int, crawler: str
    ) -> RawDocument:
        return self.make_document(
            source=source,
            id=doc_id,
            kind="medium",
            origin="external",
            content=article.content,
            author=article.author or "unknown",
            query=query,
            rank=rank,
            topics=topics,
            title=article.title,
            url=article.url,
            created_at=article.published_at,
            metadata={"medium_tags": article.tags, "member_only": article.member_only, "crawler": crawler},
        )

    def health_check(self, *, offline: bool = False) -> SourceHealth:
        if offline or not self.sources:
            return self.health(True, f"{len(self.sources)} Medium sources (browser check skipped)")
        probe = self.sources[0].typed_spec.listing_url
        try:
            with self._browser() as b:
                found = MediumListingPage(b, max_scrolls=0).collect(probe, limit=50)
        except SourceError as exc:
            return self.health(False, str(exc), probe=probe)
        return self.health(bool(found), f"{len(self.sources)} sources; {probe}: {len(found)} article links")
