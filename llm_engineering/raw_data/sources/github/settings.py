from pydantic import Field

from llm_engineering.raw_data.sources.base.provider_settings import BaseProviderSettings


class GitHubSettings(BaseProviderSettings):
    request_delay_s: float = Field(0.5, ge=0)  # between raw file downloads
