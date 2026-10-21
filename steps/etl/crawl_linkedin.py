from typing import Annotated, Any

from zenml import step
from zenml.types import HTMLString

from steps.etl.zenml_helpers import run_crawl_step


@step
def crawl_linkedin(
    selection: dict[str, list[str]],
) -> tuple[Annotated[dict[str, Any], "linkedin_summary"], Annotated[HTMLString, "linkedin_report"]]:
    """LinkedIn export sources (each user's own posts, comments, articles).

    Crawls only the `linkedin` sources in `selection`. The `linkedin_report` artifact lists every source
    and every link/file under it with ok / failed / skipped (dashboard → step → artifacts).
    """
    summary, report = run_crawl_step("linkedin", selection)
    return summary, report  # a literal tuple: ZenML reads this to register two output artifacts
