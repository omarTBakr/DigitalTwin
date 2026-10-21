from typing import Annotated, Any

from zenml import step
from zenml.types import HTMLString

from steps.etl.zenml_helpers import run_crawl_step


@step
def crawl_obsidian(
    selection: dict[str, list[str]],
) -> tuple[Annotated[dict[str, Any], "obsidian_summary"], Annotated[HTMLString, "obsidian_report"]]:
    """Obsidian vault sources.

    Crawls only the `obsidian` sources in `selection`. The `obsidian_report` artifact lists every source
    and every link/file under it with ok / failed / skipped (dashboard → step → artifacts).
    """
    summary, report = run_crawl_step("obsidian", selection)
    return summary, report  # a literal tuple: ZenML reads this to register two output artifacts
