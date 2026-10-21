from typing import Any

from zenml import get_step_context, log_metadata
from zenml.types import HTMLString

from steps.etl.crawl import crawl_provider
from steps.etl.html_report import render_crawl_report


def current_run_id() -> str:
    """The ZenML pipeline run name, stored in provenance and source state."""
    return get_step_context().pipeline_run.name


def log_summary(summary: dict[str, Any]) -> None:
    """Attach a summary to the running step (visible in the ZenML dashboard)."""
    log_metadata(metadata={k: v for k, v in summary.items() if v is not None})


def run_crawl_step(provider: str, selection: dict[str, list[str]]) -> tuple[dict[str, Any], HTMLString]:
    """Body of every crawl step: crawl this provider's selected sources, log metadata,
    and return (summary, HTML report artifact)."""
    summary, report = crawl_provider(provider, selection.get(provider, []), current_run_id())
    log_summary(summary)
    return summary, HTMLString(render_crawl_report(report))
