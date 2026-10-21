from datetime import datetime

from pydantic import BaseModel


class Provenance(BaseModel):
    """How a document was found: which registered source, which page/feed/query, in which run."""

    source_id: str
    query: str
    rank: int | None = None
    run_id: str
    collected_at: datetime
