from collections.abc import Iterator
from contextlib import ExitStack, contextmanager
from typing import ClassVar

from llm_engineering.exceptions import AccessBlockedError, SourceError
from llm_engineering.infrastructure.web.browser import Browser
from llm_engineering.raw_data.documents.raw_document import RawDocument
from llm_engineering.raw_data.sources.base.extractor import BaseExtractor
from llm_engineering.raw_data.sources.base.health import SourceHealth
from llm_engineering.raw_data.sources.medium.feed_client import MediumFeedClient, feed_url_for_article
from llm_engineering.raw_data.sources.medium.feed_entry import FeedEntry
from llm_engineering.raw_data.sources.medium.listing_page import MediumListingPage, article_id
from llm_engineering.raw_data.sources.medium.settings import MediumSettings
from llm_engineering.registry.models.source import Source
from llm_engineering.registry.specs.medium_author import MediumAuthorSpec
from llm_engineering.registry.specs.medium_tag import MediumTagSpec

CRAWLER = "medium_rss"


class MediumExtractor(BaseExtractor[MediumSettings]):
    """Medium through its official RSS feeds — no article pages are scraped.

    medium_author: the author's feed; free posts arrive with full text, member-only posts as a preview
                   (skipped).
    medium_tag:    the browser *discovers* the tag's top article links (if the tag page is blocked, the
                   tag's RSS feed gives its latest links instead); each article's full text is then looked
                   up in its author's or publication's feed. Articles that aren't there (older than the
                   feed's latest ~10 posts, or member-only) are skipped.

    Topics: tag sources give their topics plus the article's mapped tags; author sources keep only the
    article's mapped tags that the author is followed for (all of them if none map).
    Per-topic caps hold across runs (existing topics come from the store via the context).
    """

    provider: ClassVar[str] = "medium"

    @contextmanager
    def session(self):
        s = self.settings
        self.counts = self.context.topic_counts()
        self.known = {doc_id: set(topics) for doc_id, topics in self.context.existing_topics.items()}
        with ExitStack() as stack:
            self.feeds = stack.enter_context(
                MediumFeedClient(source=self.provider, delay_s=s.feed_delay_s, max_retries=s.feed_max_retries)
            )
            self.listing = None
            self.listing_blocked = False
            if any(src.type == "medium_tag" for src in self.sources):  # the browser is only for tag discovery
                self.listing = MediumListingPage(stack.enter_context(self._browser()), max_scrolls=s.max_scrolls)
            yield

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

    def extract_source(self, source: Source) -> Iterator[RawDocument]:
        spec: MediumTagSpec | MediumAuthorSpec = source.typed_spec
        if all(self.counts[t] >= self.settings.limit_per_topic for t in spec.topics):
            self.record_skipped(spec.listing_url, f"topics {spec.topics} already at cap")
            return
        if isinstance(spec, MediumAuthorSpec):
            yield from self._author_articles(source, spec)
        else:
            yield from self._tag_articles(source, spec)

    def _author_articles(self, source: Source, spec: MediumAuthorSpec) -> Iterator[RawDocument]:
        for rank, entry in enumerate(self.feeds.author_feed(spec.handle), start=1):
            if doc := self._accept(source, spec, entry, rank):
                yield doc

    def _tag_articles(self, source: Source, spec: MediumTagSpec) -> Iterator[RawDocument]:
        urls = self._discover(spec)
        for rank, url in enumerate(urls, start=1):
            if all(self.counts[t] >= self.settings.limit_per_topic for t in spec.topics):
                return
            entry = self._find_in_feed(url)
            if entry is not None and (doc := self._accept(source, spec, entry, rank)):
                yield doc

    def _discover(self, spec: MediumTagSpec) -> list[str]:
        """The tag's top links from its page (browser); if the page is blocked, its latest links from the
        tag's official RSS feed instead."""
        missing = max(self.settings.limit_per_topic - self.counts[t] for t in spec.topics)
        if self.listing is not None and not self.listing_blocked:
            try:
                urls = self.listing.collect(spec.listing_url, limit=missing * 2)  # extra: some get skipped
                self.log.info("%s: %d top article links", spec.listing_url, len(urls))
                return urls
            except AccessBlockedError as exc:
                self.listing_blocked = True  # don't retry the browser for the other tags of this run
                self.log.warning("%s; discovering via the tag's RSS feed instead", exc)
        urls = [e.url for e in self.feeds.tag_feed(spec.tag)]
        self.log.info("%s RSS: %d latest article links", spec.tag, len(urls))
        return urls

    def _find_in_feed(self, url: str) -> FeedEntry | None:
        """The article's full text from its author's/publication's official feed, or None (recorded)."""
        feed_url = feed_url_for_article(url)
        if feed_url is None:
            self.record_skipped(url, "no Medium feed for this URL")
            return None
        try:
            entries = self.feeds.entries(feed_url)
        except SourceError as exc:
            self.record_failed(url, f"feed {feed_url}: {exc}")
            return None
        wanted = article_id(url)
        entry = next((e for e in entries if e.article_id == wanted), None)
        if entry is None:
            self.record_skipped(url, f"not in {feed_url} (feeds carry only the latest ~10 posts)")
        return entry

    def _accept(
        self, source: Source, spec: MediumTagSpec | MediumAuthorSpec, entry: FeedEntry, rank: int
    ) -> RawDocument | None:
        """Caps, member-only and duplicate checks; returns the document to store or None (recorded)."""
        limit = self.settings.limit_per_topic
        doc_id = f"medium:{entry.article_id}"
        already = self.known.get(doc_id, set())
        if set(spec.topics) <= already:
            self.record_skipped(entry.url, "already stored for these topics")
            return None
        if not entry.full_text:
            self.record_skipped(entry.url, "member-only story (feed has a preview only)")
            return None
        topics = self.article_topics(spec, entry.tags)
        accepted = {t for t in topics - already if self.counts[t] < limit}
        if not accepted:
            self.record_skipped(entry.url, f"topics {sorted(topics - already)} already at cap")
            return None
        for t in accepted:
            self.counts[t] += 1
        self.known[doc_id] = already | accepted
        return self.make_document(
            source=source,
            id=doc_id,
            kind="medium",
            origin="external",
            content=entry.content,
            author=entry.author or "unknown",
            query=spec.listing_url,
            rank=rank,
            topics=self.known[doc_id],
            title=entry.title,
            url=entry.url,
            created_at=entry.published_at,
            metadata={"medium_tags": entry.tags, "crawler": CRAWLER},
        )

    def article_topics(self, spec: MediumTagSpec | MediumAuthorSpec, tags: list[str]) -> set[str]:
        mapped = self.context.matcher.from_tags(tags)
        if isinstance(spec, MediumTagSpec):
            return set(spec.topics) | mapped
        return (mapped & set(spec.topics)) or set(spec.topics)

    def health_check(self, *, offline: bool = False) -> SourceHealth:
        authors = [s.typed_spec for s in self.sources if s.type == "medium_author"]
        if offline or not authors:
            return self.health(True, f"{len(self.sources)} Medium sources (network check skipped)")
        s = self.settings
        try:
            with MediumFeedClient(source=self.provider, delay_s=s.feed_delay_s, max_retries=s.feed_max_retries) as feeds:
                entries = feeds.author_feed(authors[0].handle)
        except SourceError as exc:
            return self.health(False, str(exc))
        full = sum(e.full_text for e in entries)
        summary = f"{len(self.sources)} sources; {authors[0].handle} feed: {len(entries)} posts, {full} full text"
        return self.health(bool(entries), summary)
