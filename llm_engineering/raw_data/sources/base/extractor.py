import logging
from abc import ABC, abstractmethod
from collections.abc import Iterator
from contextlib import AbstractContextManager, nullcontext
from typing import Any, ClassVar

from llm_engineering.exceptions import (
    AccessBlockedError,
    AuthenticationError,
    RateLimitError,
    SourceError,
)
from llm_engineering.raw_data.documents.provenance import Provenance
from llm_engineering.raw_data.documents.raw_document import RawDocument
from llm_engineering.raw_data.documents.types import Origin, SourceKind
from llm_engineering.raw_data.sources.base.context import CrawlContext
from llm_engineering.raw_data.sources.base.health import SourceHealth
from llm_engineering.raw_data.sources.base.provider_settings import BaseProviderSettings
from llm_engineering.raw_data.sources.base.report import CrawlReport
from llm_engineering.registry.models.source import Source
from llm_engineering.utils.dates import utc_now
from llm_engineering.utils.hashing import content_hash

# These stop the whole provider: retrying the next source would hit the same wall.
PROVIDER_WIDE_ERRORS = (AccessBlockedError, AuthenticationError, RateLimitError)


class BaseExtractor[S: BaseProviderSettings](ABC):
    """One provider (medium, github, ...) crawling a list of registered sources of its types.

    Subclasses implement `extract_source` and `health_check`, and may override `session` to hold a
    resource (a browser, an HTTP client) open for all sources of the run.

    Errors: a SourceError inside one source marks that source failed and moves on to the next;
    PROVIDER_WIDE_ERRORS stop the provider. Per-item problems are recorded with `record_failed` /
    `record_skipped` and skipped. Every yielded document counts as "ok" (recorded by the caller).
    """

    provider: ClassVar[str]

    def __init__(self, settings: S, sources: list[Source], context: CrawlContext):
        self.settings = settings
        self.sources = sources
        self.context = context
        self.log = logging.getLogger(type(self).__module__)
        self.report = CrawlReport(provider=self.provider, source_ids=[s.id for s in sources])
        self._current: Source | None = None

    def extract(self) -> Iterator[RawDocument]:
        """Template method: open the session, crawl each source, keep going past per-source failures."""
        try:
            with self.session():
                for index, source in enumerate(self.sources):
                    self._current = source
                    try:
                        yield from self.extract_source(source)
                    except PROVIDER_WIDE_ERRORS as exc:
                        self._abort(exc, failed=self.sources[index:])
                        raise
                    except SourceError as exc:
                        self.log.warning("%s: %s", source.id, exc)
                        self.report.source_failed(source.id, str(exc))
        except SourceError as exc:
            if self.report.aborted is None:  # the session itself failed (e.g. the browser didn't start)
                self._abort(exc, failed=self.sources)
            raise
        finally:
            self._current = None
            self._fail_sources_without_successes()

    def _abort(self, exc: SourceError, failed: list[Source]) -> None:
        """Provider-wide stop: record why, and mark the source being crawled and all later ones failed."""
        self.report.aborted = str(exc)
        for i, source in enumerate(failed):
            self.report.source_failed(source.id, str(exc) if i == 0 else f"not crawled: provider stopped early ({exc})")

    def _fail_sources_without_successes(self) -> None:
        """A source whose every attempted item failed counts as failed, even if no exception was raised."""
        for source_id in self.report.source_ids:
            counts = self.report.counts(source_id)
            if source_id not in self.report.source_errors and counts["failed"] and not counts["ok"]:
                self.report.source_failed(source_id, f"all {counts['failed']} attempted items failed")

    def session(self) -> AbstractContextManager[Any]:
        """Resource shared by all sources of a run. Default: none."""
        return nullcontext()

    @abstractmethod
    def extract_source(self, source: Source) -> Iterator[RawDocument]:
        """Yield the documents of one registered source."""

    @abstractmethod
    def health_check(self, *, offline: bool = False) -> SourceHealth:
        """Report whether the provider's sources are configured and reachable. `offline` skips network."""

    # ------------------------------------------------------------- helpers for subclasses

    @property
    def current(self) -> Source:
        if self._current is None:
            raise RuntimeError("no source is being extracted")
        return self._current

    def record_failed(self, item: str, reason: str) -> None:
        self.report.failed(self.current.id, item, reason)

    def record_skipped(self, item: str, reason: str) -> None:
        self.report.skipped(self.current.id, item, reason)

    def make_document(
        self,
        *,
        source: Source,
        id: str,
        kind: SourceKind,
        origin: Origin,
        content: str,
        author: str,
        query: str,
        rank: int | None = None,
        topics: set[str] | list[str] = (),
        owned: bool = True,
        **fields: Any,
    ) -> RawDocument:
        """Build a RawDocument with provider, ownership, source link, hash and provenance filled consistently.

        `owned=False` marks third-party content found in a user's own source (e.g. a PDF in their vault):
        it gets no owner_id, so it never counts as the user's writing."""
        return RawDocument(
            id=id,
            provider=self.provider,
            source=kind,
            owner_id=source.owner_id if owned else None,
            source_ids=[source.id],
            origin=origin,
            content=content,
            author=author,
            content_hash=content_hash(content),
            topics=sorted(topics),
            provenance=[
                Provenance(source_id=source.id, query=query, rank=rank, run_id=self.context.run_id, collected_at=utc_now())
            ],
            **fields,
        )

    def health(self, ok: bool, summary: str, **details: Any) -> SourceHealth:
        return SourceHealth(source=self.provider, ok=ok, summary=summary, details=details)
