from typing import Annotated, Any

from zenml import step
from zenml.types import HTMLString

from steps.etl.zenml_helpers import run_crawl_step


@step
def crawl_medium(
    selection: dict[str, list[str]],
) -> tuple[Annotated[dict[str, Any], "medium_summary"], Annotated[HTMLString, "medium_report"]]:
    """Medium tag and author sources (Selenium).

    Crawls only the `medium` sources in `selection`. The `medium_report` artifact lists every source
    and every link/file under it with ok / failed / skipped (dashboard → step → artifacts).
    """
    summary, report = run_crawl_step("medium", selection)
    return summary, report  # a literal tuple: ZenML reads this to register two output artifacts
