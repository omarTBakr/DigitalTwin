from pydantic import Field

from llm_engineering.raw_data.sources.base.provider_settings import BaseProviderSettings


class MediumSettings(BaseProviderSettings):
    limit_per_topic: int = Field(100, gt=0)  # cap across runs, counted from the store
    skip_member_only: bool = True  # member-only stories show a preview only without login
    use_fallback: bool = True  # retry failed article pages with CustomArticleCrawler (plain HTTP)
    headless: bool = True  # set False if Medium shows a bot challenge
    page_load_timeout_s: float = Field(30, gt=0)
    scroll_pause_s: float = Field(2.0, ge=0)
    max_scrolls: int = Field(30, ge=0)
    request_delay_s: float = Field(3.0, ge=0)
