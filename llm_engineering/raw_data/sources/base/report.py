from collections import Counter
from dataclasses import dataclass, field
from typing import Literal

ItemStatus = Literal["ok", "failed", "skipped"]
STATUSES: tuple[ItemStatus, ...] = ("ok", "failed", "skipped")


@dataclass
class ItemOutcome:
    """What happened to one link / file / note during a crawl."""

    source_id: str  # registered source it belongs to
    item: str  # URL, repo path or vault path
    status: ItemStatus
    title: str | None = None
    topics: list[str] = field(default_factory=list)
    reason: str | None = None  # why it failed or was skipped


@dataclass
class CrawlReport:
    """Outcomes of one provider run, per source and per item — shown in the ZenML dashboard and
    used to update each source's state in the registry."""

    provider: str
    source_ids: list[str] = field(default_factory=list)  # every source this run crawled
    outcomes: list[ItemOutcome] = field(default_factory=list)
    source_errors: dict[str, str] = field(default_factory=dict)  # source id -> why the source failed
    aborted: str | None = None  # set when the whole provider stopped early (blocked, auth, rate limit)

    def ok(self, source_id: str, item: str, title: str | None = None, topics: list[str] | None = None) -> None:
        self.outcomes.append(ItemOutcome(source_id, item, "ok", title, topics or []))

    def failed(self, source_id: str, item: str, reason: str) -> None:
        self.outcomes.append(ItemOutcome(source_id, item, "failed", reason=reason))

    def skipped(self, source_id: str, item: str, reason: str) -> None:
        self.outcomes.append(ItemOutcome(source_id, item, "skipped", reason=reason))

    def source_failed(self, source_id: str, reason: str) -> None:
        self.source_errors[source_id] = reason

    def counts(self, source_id: str | None = None) -> dict[str, int]:
        counter = Counter(o.status for o in self.outcomes if source_id is None or o.source_id == source_id)
        return {status: counter.get(status, 0) for status in STATUSES}
