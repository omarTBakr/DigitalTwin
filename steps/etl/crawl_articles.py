from typing import Annotated, Any

from zenml import step
from zenml.types import HTMLString

from steps.etl.zenml_helpers import run_crawl_step


@step
def crawl_articles(
    selection: dict[str, list[str]],
) -> tuple[Annotated[dict[str, Any], "articles_summary"], Annotated[HTMLString, "articles_report"]]:
    """Single web-article sources, via CustomArticleCrawler.

    Crawls only the `articles` sources in `selection`. The `articles_report` artifact lists every source
    and every link/file under it with ok / failed / skipped (dashboard → step → artifacts).
    """
    summary, report = run_crawl_step("articles", selection)
    return summary, report  # a literal tuple: ZenML reads this to register two output artifacts
