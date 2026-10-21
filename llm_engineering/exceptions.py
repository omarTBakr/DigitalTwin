"""Project-wide exception hierarchy.

    DigitalTwinError
    ├── ConfigError                    bad or missing configuration — fix the YAML, don't retry
    │   ├── ConfigNotFoundError
    │   ├── ConfigParseError           not valid YAML
    │   ├── ConfigValidationError      valid YAML, fails the Pydantic models
    │   ├── UnknownSourceError
    │   └── UnknownUserError
    ├── SourceError                    a source failed while extracting (carries `source`)
    │   ├── SourceUnavailableError     unreachable / missing (network down, no vault, no export)
    │   │   ├── RateLimitError         throttled; `retry_after` seconds if known
    │   │   └── AccessBlockedError     bot challenge / captcha — retrying now won't help
    │   ├── AuthenticationError        credentials missing or rejected
    │   └── ParseError                 one item couldn't be parsed — usually logged and skipped
    ├── StorageError
    │   ├── StorageUnavailableError    database unreachable (is MongoDB running? MONGO_URI?)
    │   ├── RegistryError              users/sources/subscriptions storage failed
    │   └── StoreCorruptedError        a stored record can't be read back
    ├── VersioningError                DVC/git snapshotting failed (data in the store is unaffected)
    └── PipelineError                  a pipeline finished but some of its work failed

Policy: item-level errors (ParseError) are handled inside extractors (log + skip);
source-level errors propagate to the caller, which records the failure and moves on to the next
source; ConfigError stops the run before anything is fetched.
"""

from pathlib import Path


class DigitalTwinError(Exception):
    """Base class: `except DigitalTwinError` catches every error this project raises on purpose."""


# ---------------------------------------------------------------- config


class ConfigError(DigitalTwinError):
    def __init__(self, message: str, *, path: Path | None = None):
        self.path = path
        super().__init__(f"{path}: {message}" if path else message)


class ConfigNotFoundError(ConfigError):
    pass


class ConfigParseError(ConfigError):
    pass


class ConfigValidationError(ConfigError):
    pass


class UnknownSourceError(ConfigError):
    pass


class UnknownUserError(ConfigError):
    pass


# ---------------------------------------------------------------- sources


class SourceError(DigitalTwinError):
    def __init__(self, message: str, *, source: str | None = None):
        self.source = source
        super().__init__(f"[{source}] {message}" if source else message)


class SourceUnavailableError(SourceError):
    pass


class RateLimitError(SourceUnavailableError):
    def __init__(self, message: str, *, source: str | None = None, retry_after: float | None = None):
        self.retry_after = retry_after
        super().__init__(message, source=source)


class AccessBlockedError(SourceUnavailableError):
    pass


class AuthenticationError(SourceError):
    pass


class ParseError(SourceError):
    def __init__(self, message: str, *, source: str | None = None, item: str | None = None):
        self.item = item
        super().__init__(f"{item}: {message}" if item else message, source=source)


# ---------------------------------------------------------------- storage


class StorageError(DigitalTwinError):
    pass


class StorageUnavailableError(StorageError):
    pass


class RegistryError(StorageError):
    pass


class StoreCorruptedError(StorageError):
    def __init__(self, message: str, *, location: str):
        self.location = location  # e.g. "raw_documents/<_id>"
        super().__init__(f"{location}: {message}")


# ---------------------------------------------------------------- versioning


class VersioningError(DigitalTwinError):
    pass


# ---------------------------------------------------------------- pipelines


class PipelineError(DigitalTwinError):
    pass
