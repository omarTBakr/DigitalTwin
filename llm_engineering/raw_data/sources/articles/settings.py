from pydantic import Field

from llm_engineering.raw_data.sources.base.provider_settings import BaseProviderSettings


class ArticlesSettings(BaseProviderSettings):
    request_delay_s: float = Field(1.0, ge=0)  # between article downloads
    min_chars: int = Field(200, ge=0)  # pages with less text are treated as failed crawls
