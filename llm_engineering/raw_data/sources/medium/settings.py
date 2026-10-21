from pathlib import Path

from pydantic import Field, model_validator

from llm_engineering.raw_data.sources.base.provider_settings import BaseProviderSettings


class MediumSettings(BaseProviderSettings):
    limit_per_topic: int = Field(100, gt=0)  # cap across runs, counted from the store
    skip_member_only: bool = True  # member-only stories show a preview only without login
    # official RSS feeds (full text of free posts)
    feed_delay_s: float = Field(3.0, ge=0)  # between feed requests (Medium rate-limits fast clients)
    feed_max_retries: int = Field(3, ge=0)
    # browser: only used to discover a tag's top article links
    headless: bool = True  # set False if Medium shows a bot challenge
    browser_binary: str | None = None  # path to a Chromium-based browser (e.g. Brave); None = Google Chrome
    # persistent profile = your logins/cookies (log in to Medium once in it). Close that browser before a run.
    user_data_dir: Path | None = None
    profile_directory: str | None = None  # e.g. "Default", "Profile 1" inside user_data_dir
    page_load_timeout_s: float = Field(30, gt=0)
    max_scrolls: int = Field(80, ge=0)  # mouse-wheel steps per listing page (a few hundred px each)
    action_delay_min_s: float = Field(2.0, ge=0)  # random pause between page loads / scroll steps
    action_delay_max_s: float = Field(5.0, ge=0)

    @model_validator(mode="after")
    def _delays_ordered(self):
        if self.action_delay_max_s < self.action_delay_min_s:
            raise ValueError("action_delay_max_s must be >= action_delay_min_s")
        return self
