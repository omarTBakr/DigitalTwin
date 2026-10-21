"""Providers: who crawls which registered sources. Adding a provider = a `sources/<provider>/` package
(settings.py + extractor.py) + one entry here; its source types are specs whose `provider` names it."""

from dataclasses import dataclass

from llm_engineering.exceptions import UnknownSourceError
from llm_engineering.raw_data.sources.articles.extractor import ArticlesExtractor
from llm_engineering.raw_data.sources.articles.settings import ArticlesSettings
from llm_engineering.raw_data.sources.base.context import CrawlContext
from llm_engineering.raw_data.sources.base.extractor import BaseExtractor
from llm_engineering.raw_data.sources.base.provider_settings import BaseProviderSettings
from llm_engineering.raw_data.sources.github.extractor import GitHubExtractor
from llm_engineering.raw_data.sources.github.settings import GitHubSettings
from llm_engineering.raw_data.sources.linkedin.extractor import LinkedInExportExtractor
from llm_engineering.raw_data.sources.linkedin.settings import LinkedInSettings
from llm_engineering.raw_data.sources.medium.extractor import MediumExtractor
from llm_engineering.raw_data.sources.medium.settings import MediumSettings
from llm_engineering.raw_data.sources.obsidian.extractor import ObsidianExtractor
from llm_engineering.raw_data.sources.obsidian.settings import ObsidianSettings
from llm_engineering.registry.models.source import Source


@dataclass(frozen=True)
class Provider:
    name: str
    settings_model: type[BaseProviderSettings]
    extractor_class: type[BaseExtractor]


PROVIDERS: dict[str, Provider] = {
    p.name: p
    for p in (
        Provider("medium", MediumSettings, MediumExtractor),
        Provider("github", GitHubSettings, GitHubExtractor),
        Provider("linkedin", LinkedInSettings, LinkedInExportExtractor),
        Provider("obsidian", ObsidianSettings, ObsidianExtractor),
        Provider("articles", ArticlesSettings, ArticlesExtractor),
    )
}


def get_provider(name: str) -> Provider:
    try:
        return PROVIDERS[name]
    except KeyError:
        raise UnknownSourceError(f"unknown provider {name!r}; choose from {sorted(PROVIDERS)}") from None


def create_extractor(
    provider: str, settings: BaseProviderSettings, sources: list[Source], context: CrawlContext
) -> BaseExtractor:
    return get_provider(provider).extractor_class(settings, sources, context)
