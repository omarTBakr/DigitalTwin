import time
from collections.abc import Iterator
from typing import ClassVar

from llm_engineering.exceptions import ParseError, SourceUnavailableError
from llm_engineering.raw_data.crawlers.custom_article_crawler import (
    CustomArticleCrawler,
)
from llm_engineering.raw_data.documents.raw_document import RawDocument
from llm_engineering.raw_data.sources.articles.settings import ArticlesSettings
from llm_engineering.raw_data.sources.base.extractor import BaseExtractor
from llm_engineering.raw_data.sources.base.health import SourceHealth
from llm_engineering.registry.models.source import Source
from llm_engineering.registry.specs.article import ArticleSpec
from llm_engineering.utils.hashing import short_id


class ArticlesExtractor(BaseExtractor[ArticlesSettings]):
    """Registered article URLs, crawled with CustomArticleCrawler. A failed URL fails only its source."""

    provider: ClassVar[str] = "articles"

    @property
    def crawler(self) -> CustomArticleCrawler:
        return CustomArticleCrawler(source=self.provider, min_chars=self.settings.min_chars)

    def extract_source(self, source: Source) -> Iterator[RawDocument]:
        spec: ArticleSpec = source.typed_spec
        if source is not self.sources[0]:
            time.sleep(self.settings.request_delay_s)
        url = str(spec.url)
        try:
            article = self.crawler.crawl(url)
        except ParseError as exc:  # page fetched but no usable text: record it, mark the source failed
            self.record_failed(url, str(exc))
            raise SourceUnavailableError(str(exc), source=source.id) from exc
        except SourceUnavailableError as exc:
            self.record_failed(url, str(exc))
            raise
        yield self.make_document(
            source=source,
            id=f"article:{short_id(source.id)}",
            kind="article",
            origin=spec.origin,
            content=article.content,
            author=spec.url.host or "unknown",  # the site; plain-text crawling has no reliable byline
            query=url,
            topics=spec.topics,
            title=article.title,
            url=url,
            metadata=article.metadata,
        )

    def health_check(self, *, offline: bool = False) -> SourceHealth:
        if offline or not self.sources:
            return self.health(True, f"{len(self.sources)} article URLs (network check skipped)")
        probe = str(self.sources[0].typed_spec.url)
        try:
            article = self.crawler.crawl(probe)
        except (ParseError, SourceUnavailableError) as exc:
            return self.health(False, str(exc), probe=probe)
        return self.health(True, f"{len(self.sources)} article URLs; {probe}: {len(article.content)} chars")
