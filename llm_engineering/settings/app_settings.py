"""Application settings: the one place that reads the environment.

Values come from real environment variables first, then the repo-root `.env` file (git-ignored;
see `.env.example`), then the defaults below. Each group reads its own prefix:

    MONGO_*      MongoDB connection          settings.mongo
    GITHUB_*     GitHub API                  settings.github
    DVC_*        raw data versioning         settings.versioning
    RAW_STORE_*  raw data store backend      settings.raw_store

Use `get_settings()` (cached) instead of instantiating these classes.
"""

from functools import cache
from pathlib import Path
from typing import Literal
from urllib.parse import quote_plus, urlencode

from pydantic import BaseModel, Field, SecretStr, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from llm_engineering.exceptions import ConfigValidationError
from llm_engineering.settings.paths import ENV_FILE, RAW_SNAPSHOT_DIR, from_root

StoreBackend = Literal["mongo"]  # add a backend here and in raw_data/store/factory.py


def _env(prefix: str) -> SettingsConfigDict:
    return SettingsConfigDict(env_prefix=prefix, env_file=ENV_FILE, env_file_encoding="utf-8", extra="ignore")


class MongoSettings(BaseSettings):
    """Either set MONGO_URI to a full connection string, or set the parts and one is built for you."""

    model_config = _env("MONGO_")

    uri: SecretStr | None = None  # full override, e.g. a MongoDB Atlas "mongodb+srv://..." string
    scheme: Literal["mongodb", "mongodb+srv"] = "mongodb"
    host: str = "localhost"
    port: int | None = 27017  # ignored for mongodb+srv
    username: str | None = None
    password: SecretStr | None = None
    database: str = "digital_twin"
    auth_source: str | None = "admin"  # only sent when credentials are set
    options: dict[str, str] = Field(default_factory=dict)  # e.g. MONGO_OPTIONS='{"tls": "true"}'
    timeout_ms: int = 5000

    @property
    def connection_string(self) -> str:
        """The URI handed to MongoClient (contains the password — never log it; use `display_uri`)."""
        if self.uri is not None:
            return self.uri.get_secret_value()
        return self._build(self.password.get_secret_value() if self.password else None)

    @property
    def display_uri(self) -> str:
        """The connection string with the password masked, safe for logs and error messages."""
        if self.uri is not None:
            return "<MONGO_URI>"
        return self._build("***" if self.password else None)

    def _build(self, password: str | None) -> str:
        credentials = ""
        if self.username:
            credentials = quote_plus(self.username)
            if password is not None:
                credentials += f":{password if password == '***' else quote_plus(password)}"
            credentials += "@"
        port = f":{self.port}" if self.port and self.scheme == "mongodb" else ""
        query = dict(self.options)
        if self.username and self.auth_source:
            query.setdefault("authSource", self.auth_source)
        suffix = f"?{urlencode(query)}" if query else ""
        return f"{self.scheme}://{credentials}{self.host}{port}/{self.database}{suffix}"


class GitHubSettings(BaseSettings):
    """Optional token: raises the API limit from 60 to 5000 requests/hour; needed for private repos."""

    model_config = _env("GITHUB_")

    token: SecretStr | None = None


class VersioningSettings(BaseSettings):
    """DVC snapshotting of raw data."""

    model_config = _env("DVC_")

    enabled: bool = True
    snapshot_dir: Path = RAW_SNAPSHOT_DIR
    auto_commit: bool = True  # git-commit the .dvc pointer files after `dvc add`
    auto_push: bool = True  # `dvc push` to the remote
    remote: str | None = None  # None = the default remote in .dvc/config

    @field_validator("snapshot_dir")
    @classmethod
    def _anchor(cls, v: Path) -> Path:
        return from_root(v)


class RawStoreSettings(BaseSettings):
    model_config = _env("RAW_STORE_")

    backend: StoreBackend = "mongo"


class Settings(BaseModel):
    mongo: MongoSettings = Field(default_factory=MongoSettings)
    github: GitHubSettings = Field(default_factory=GitHubSettings)
    versioning: VersioningSettings = Field(default_factory=VersioningSettings)
    raw_store: RawStoreSettings = Field(default_factory=RawStoreSettings)


@cache
def get_settings() -> Settings:
    """Load once per process. A bad value (e.g. MONGO_PORT=abc) raises ConfigValidationError."""
    try:
        return Settings()
    except ValidationError as exc:
        raise ConfigValidationError(f"invalid settings in environment or {ENV_FILE}: {exc}") from exc
