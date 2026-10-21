import logging
from typing import Any

from zenml import step

from llm_engineering.exceptions import PipelineError

log = logging.getLogger(__name__)


def format_summary(summary: dict[str, Any]) -> str:
    lines = [f"{summary['provider']}: {summary['status']}"]
    if summary["status"] == "skipped":
        return lines[0] + " (no sources selected)"
    lines[0] += (
        f" — {summary['sources']} sources ({len(summary['sources_failed'])} failed); "
        f"items ok {summary['items_ok']}, failed {summary['items_failed']}, skipped {summary['items_skipped']}; "
        f"new {summary['inserted']}, refreshed {summary['matched']}, stored total {summary['stored_total']}"
    )
    if summary.get("error"):
        lines.append(f"  stopped early: {summary['error']}")
    for source_id in summary["sources_failed"]:
        lines.append(f"  failed source: {source_id}")
    limit = summary.get("limit_per_topic")
    for topic, n in sorted(summary.get("topics", {}).items(), key=lambda kv: -kv[1]):
        cap = f" / {limit}" if limit else ""
        lines.append(f"  {topic:<24} {n:>5}{cap}")
    return "\n".join(lines)


@step
def summarize_crawl(crawl_summaries: list[dict[str, Any]], versioning: dict[str, Any]) -> None:
    """Log per-provider results. Fail the run (after everything ran) if a provider failed or versioning
    failed; `partial` providers (some sources failed) are logged as warnings — see each source's state."""
    for summary in crawl_summaries:
        (log.warning if summary["status"] == "partial" else log.info)("\n%s", format_summary(summary))
    log.info("versioning: %s", versioning)

    problems = [s["provider"] for s in crawl_summaries if s["status"] == "failed"]
    if versioning.get("status") == "failed":
        problems.append(f"versioning ({versioning.get('error')})")
    if problems:
        raise PipelineError(f"failed: {problems} (crawled data was saved)")
