from datetime import datetime
from typing import Literal

from pydantic import BaseModel

SourceStatus = Literal["never", "ok", "failed"]


class SourceState(BaseModel):
    """Outcome of the latest crawl of one source — what triggers and a UI will read."""

    status: SourceStatus = "never"
    last_run_id: str | None = None
    last_crawled_at: datetime | None = None
    error: str | None = None
    items_ok: int = 0
    items_failed: int = 0
    items_skipped: int = 0
