from pydantic import BaseModel, ConfigDict


class BaseProviderSettings(BaseModel):
    """Crawler tuning shared by every source of one provider (configs/providers/<provider>.yaml).

    Per-source choices (which tag, which repos, which vault) live in the source specs instead.
    """

    model_config = ConfigDict(extra="forbid")  # catches typos in YAML keys
