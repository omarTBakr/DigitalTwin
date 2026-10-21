"""CrawlReport -> self-contained HTML page, rendered by the ZenML dashboard (HTMLString artifact).

One section per registered source (failed sources first), each with its items as ok / failed / skipped.
"""

from html import escape

from llm_engineering.raw_data.sources.base.report import CrawlReport, ItemOutcome

STATUS_ORDER = {"failed": 0, "skipped": 1, "ok": 2}
STATUS_COLOR = {"ok": "#1a7f37", "failed": "#cf222e", "skipped": "#9a6700"}

STYLE = """
<style>
  .crawl-report { font-family: system-ui, sans-serif; font-size: 13px; color: #1f2328; }
  .crawl-report h2 { margin: 0 0 4px; }
  .crawl-report h3 { margin: 18px 0 2px; font-size: 14px; }
  .crawl-report .counts span { margin-right: 14px; font-weight: 600; }
  .crawl-report .error { background: #ffebe9; border: 1px solid #cf222e; padding: 6px 8px; margin: 6px 0; }
  .crawl-report table { border-collapse: collapse; width: 100%; margin-top: 4px; }
  .crawl-report th, .crawl-report td { border-bottom: 1px solid #d0d7de; padding: 4px 8px; text-align: left;
                                        vertical-align: top; }
  .crawl-report th { background: #f6f8fa; }
  .crawl-report .badge { color: #fff; border-radius: 10px; padding: 1px 8px; font-size: 11px; }
  .crawl-report td.item { max-width: 520px; overflow-wrap: anywhere; }
  .crawl-report .empty { color: #656d76; font-style: italic; }
</style>
"""


def _badge(status: str) -> str:
    return f'<span class="badge" style="background:{STATUS_COLOR[status]}">{status}</span>'


def _counts(counts: dict[str, int]) -> str:
    spans = "".join(f'<span style="color:{STATUS_COLOR[s]}">{s}: {n}</span>' for s, n in counts.items())
    return f'<div class="counts">{spans}</div>'


def _item_cell(item: str) -> str:
    text = escape(item)
    if item.startswith(("http://", "https://")):
        return f'<a href="{text}" target="_blank" rel="noopener">{text}</a>'
    return text


def _row(outcome: ItemOutcome) -> str:
    return (
        "<tr>"
        f"<td>{_badge(outcome.status)}</td>"
        f'<td class="item">{_item_cell(outcome.item)}</td>'
        f"<td>{escape(outcome.title or '')}</td>"
        f"<td>{escape(', '.join(outcome.topics))}</td>"
        f"<td>{escape(outcome.reason or '')}</td>"
        "</tr>"
    )


def _source_section(report: CrawlReport, source_id: str) -> str:
    error = report.source_errors.get(source_id)
    rows = sorted((o for o in report.outcomes if o.source_id == source_id), key=lambda o: (STATUS_ORDER[o.status], o.item))
    status = "failed" if error else "ok"
    body = (
        "<table><thead><tr><th>status</th><th>link / file</th><th>title</th><th>topics</th><th>reason</th></tr></thead>"
        f"<tbody>{''.join(_row(o) for o in rows)}</tbody></table>"
        if rows
        else '<div class="empty">no items</div>'
    )
    return (
        f"<h3>{_badge(status)} {escape(source_id)}</h3>"
        f"{_counts(report.counts(source_id))}"
        f"{f'<div class=error>{escape(error)}</div>' if error else ''}"
        f"{body}"
    )


def render_crawl_report(report: CrawlReport) -> str:
    source_ids = sorted(report.source_ids, key=lambda sid: (sid not in report.source_errors, sid))
    aborted = f'<div class="error"><b>Provider stopped early:</b> {escape(report.aborted)}</div>' if report.aborted else ""
    sections = "".join(_source_section(report, sid) for sid in source_ids) or '<div class="empty">no sources selected</div>'
    return (
        f'{STYLE}<div class="crawl-report">'
        f"<h2>{escape(report.provider)} — {len(source_ids)} source(s), {len(report.source_errors)} failed</h2>"
        f"{_counts(report.counts())}{aborted}{sections}</div>"
    )
