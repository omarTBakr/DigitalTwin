from zenml import pipeline

from steps.etl.crawl_articles import crawl_articles
from steps.etl.crawl_github import crawl_github
from steps.etl.crawl_linkedin import crawl_linkedin
from steps.etl.crawl_medium import crawl_medium
from steps.etl.crawl_obsidian import crawl_obsidian
from steps.etl.select_sources import select_sources
from steps.etl.summarize import summarize_crawl
from steps.etl.sync_registry import sync_registry
from steps.etl.version_raw_data import version_raw_data


@pipeline(enable_cache=False)  # crawling has side effects; never reuse a cached run
def digital_data_etl(user_id: str | None = None, source_ids: list[str] | None = None) -> None:
    """Sync the registry, crawl the selected sources into the raw data store, version a DVC snapshot.

    user_id=None, source_ids=None → every enabled source; user_id → that user's subscriptions;
    source_ids → exactly those (how triggers will call it).
    Dashboard: one step per provider; its `<provider>_report` artifact lists every source and item.
    """
    registry_sync = sync_registry()
    selection = select_sources(registry_sync=registry_sync, user_id=user_id, source_ids=source_ids)

    medium, _ = crawl_medium(selection=selection)
    github, _ = crawl_github(selection=selection)
    linkedin, _ = crawl_linkedin(selection=selection)
    obsidian, _ = crawl_obsidian(selection=selection)
    articles, _ = crawl_articles(selection=selection)

    summaries = [medium, github, linkedin, obsidian, articles]
    versioning = version_raw_data(crawl_summaries=summaries)
    summarize_crawl(crawl_summaries=summaries, versioning=versioning)
