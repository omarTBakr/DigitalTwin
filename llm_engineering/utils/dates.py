from datetime import UTC, date, datetime


def utc_now() -> datetime:
    return datetime.now(UTC)


def run_id() -> str:
    """Sortable id for one crawl run, e.g. '20261021T153000Z'."""
    return utc_now().strftime("%Y%m%dT%H%M%SZ")


def to_utc_datetime(value: object) -> datetime | None:
    """datetime / date / ISO string -> aware UTC datetime; anything else -> None. Naive values are assumed UTC."""
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day, tzinfo=UTC)
    if isinstance(value, str):
        return parse_iso_datetime(value)
    return None


def parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return to_utc_datetime(datetime.fromisoformat(value.strip()))
    except ValueError:
        return None
