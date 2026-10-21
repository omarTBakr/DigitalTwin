"""Shared body of the per-provider crawl steps (a plain function, so it also works outside ZenML)."""

import logging
from typing import Any

from llm_engineering.crawl_config.yaml_loader import YamlLoader
from llm_engineering.exceptions import SourceError
from llm_engineering.raw_data.documents.raw_document import RawDocument
from llm_engineering.raw_data.sources.base.context import CrawlContext
from llm_engineering.raw_data.sources.base.report import CrawlReport
from llm_engineering.raw_data.sources.registry import create_extractor
from llm_engineering.raw_data.store.factory import create_raw_data_store
from llm_engineering.raw_data.store.upsert_stats import UpsertStats
from llm_engineering.registry.models.source_state import SourceState
from llm_engineering.registry.store.base import RegistryStore
from llm_engineering.registry.store.factory import create_registry_store
from llm_engineering.utils.dates import utc_now

log = logging.getLogger(__name__)

BATCH_SIZE = 50  # flush to the store regularly so a crash loses at most one batch


def crawl_provider(provider: str, source_ids: list[str], run_id: str) -> tuple[dict[str, Any], CrawlReport]:
    """Crawl the given registered sources of one provider into the raw data store.

    Returns (summary, per-source/per-item report) and records each source's state in the registry.
    status: ok | partial (some sources failed) | failed (provider stopped, or every source failed) | skipped.
    ConfigError / StorageError propagate (nothing sensible to do without config or a database).
    """
    if not source_ids:
        return {"provider": provider, "status": "skipped"}, CrawlReport(provider=provider)

    config = YamlLoader()
    registry = create_registry_store()
    by_id = {s.id: s for s in registry.sources(source_ids)}
    sources = [by_id[sid] for sid in source_ids if sid in by_id]
    store = create_raw_data_store()
    store.setup()
    context = CrawlContext(
        run_id=run_id,
        topics=config.topics,
        users={u.id: u for u in registry.users()},
        existing_topics=store.topics_by_id(provider),
    )
    extractor = create_extractor(provider, config.providers[provider], sources, context)
    report = extractor.report

    totals = UpsertStats()
    batch: list[RawDocument] = []

    def flush() -> None:
        nonlocal totals
        totals += store.upsert_many(batch)
        batch.clear()

    try:
        for doc in extractor.extract():
            report.ok(doc.source_ids[0], doc.url or doc.id, doc.title, doc.topics)
            batch.append(doc)
            if len(batch) >= BATCH_SIZE:
                flush()
    except SourceError as exc:
        log.error("%s stopped after %d documents: %s", provider, report.counts()["ok"], exc)
    finally:
        flush()
        record_states(registry, report, run_id)

    failed = sorted(report.source_errors)
    status = "failed" if report.aborted or len(failed) == len(sources) else "partial" if failed else "ok"
    counts = report.counts()
    summary = {
        "provider": provider,
        "status": status,
        "error": report.aborted,
        "sources": len(sources),
        "sources_failed": failed,
        "items_ok": counts["ok"],
        "items_failed": counts["failed"],
        "items_skipped": counts["skipped"],
        "inserted": totals.inserted,
        "matched": totals.matched,
        "stored_total": store.count(provider),
        "topics": dict(store.counts_by_topic(provider)),
        "limit_per_topic": getattr(config.providers[provider], "limit_per_topic", None),
    }
    return summary, report


def record_states(registry: RegistryStore, report: CrawlReport, run_id: str) -> None:
    """Write each crawled source's outcome to the registry (what triggers and a UI will read)."""
    now = utc_now()
    for source_id in report.source_ids:
        counts = report.counts(source_id)
        error = report.source_errors.get(source_id)
        registry.record_state(
            source_id,
            SourceState(
                status="failed" if error else "ok",
                last_run_id=run_id,
                last_crawled_at=now,
                error=error,
                items_ok=counts["ok"],
                items_failed=counts["failed"],
                items_skipped=counts["skipped"],
            ),
        )
