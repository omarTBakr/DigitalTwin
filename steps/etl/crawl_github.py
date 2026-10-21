from typing import Annotated, Any

from zenml import step
from zenml.types import HTMLString

from steps.etl.zenml_helpers import run_crawl_step


@step
def crawl_github(
    selection: dict[str, list[str]],
) -> tuple[Annotated[dict[str, Any], "github_summary"], Annotated[HTMLString, "github_report"]]:
    """GitHub account sources: READMEs, docs, code and notebooks.

    Crawls only the `github` sources in `selection`. The `github_report` artifact lists every source
    and every link/file under it with ok / failed / skipped (dashboard → step → artifacts).
    """
    summary, report = run_crawl_step("github", selection)
    return summary, report  # a literal tuple: ZenML reads this to register two output artifacts
