"""All YAML configuration I/O: topics, provider tuning, and user declarations (seed data)."""

from functools import cached_property
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from llm_engineering.exceptions import (
    ConfigError,
    ConfigNotFoundError,
    ConfigParseError,
    ConfigValidationError,
    UnknownUserError,
)
from llm_engineering.raw_data.sources.base.provider_settings import BaseProviderSettings
from llm_engineering.raw_data.sources.registry import PROVIDERS
from llm_engineering.registry.models.user import User
from llm_engineering.registry.models.user_declaration import UserDeclaration
from llm_engineering.registry.specs.registry import SourceSpec, source_spec_adapter
from llm_engineering.settings.paths import PROVIDERS_DIR, TOPICS_FILE, USERS_DIR
from llm_engineering.topics.models import Topic, TopicsFile

PROFILE_FILE = "profile.yaml"
USER_SOURCES_DIR = "sources"


class YamlLoader:
    """Loads and validates the YAML configuration:

        configs/topics.yaml                      → topics
        configs/providers/<provider>.yaml        → providers   (optional; defaults when absent)
        configs/users/<id>/profile.yaml          → users       (UserDeclaration per user)
        configs/users/<id>/sources/*.yaml        →   each file: `sources: [ {type: ..., ...}, ... ]`

    Results are parsed once per loader and cached; create a new loader to re-read files.
    Every failure is a ConfigError subclass (not found, invalid YAML, failed validation, unknown user).
    """

    def __init__(self, topics_file: Path = TOPICS_FILE, providers_dir: Path = PROVIDERS_DIR, users_dir: Path = USERS_DIR):
        self.topics_file = topics_file
        self.providers_dir = providers_dir
        self.users_dir = users_dir

    @staticmethod
    def read(path: Path) -> Any:
        """Parse one YAML file."""
        try:
            with path.open(encoding="utf-8") as f:
                return yaml.safe_load(f)
        except FileNotFoundError as exc:
            raise ConfigNotFoundError("file not found", path=path) from exc
        except yaml.YAMLError as exc:
            raise ConfigParseError(f"invalid YAML: {exc}", path=path) from exc

    # ------------------------------------------------------------------ topics

    @cached_property
    def topics(self) -> dict[str, Topic]:
        """Topic key -> Topic, from the topics file."""
        try:
            return TopicsFile.model_validate(self.read(self.topics_file)).topics
        except ValidationError as exc:
            raise ConfigValidationError(str(exc), path=self.topics_file) from exc

    # ------------------------------------------------------------------ providers

    @cached_property
    def providers(self) -> dict[str, BaseProviderSettings]:
        """Provider name -> its settings (from configs/providers/<name>.yaml, or defaults)."""
        unknown = sorted(p.stem for p in self.providers_dir.glob("*.yaml") if p.stem not in PROVIDERS)
        if unknown:
            raise ConfigError(f"no provider named {unknown}; choose from {sorted(PROVIDERS)}", path=self.providers_dir)
        settings: dict[str, BaseProviderSettings] = {}
        for name, provider in PROVIDERS.items():
            path = self.providers_dir / f"{name}.yaml"
            raw = (self.read(path) or {}) if path.exists() else {}
            try:
                settings[name] = provider.settings_model.model_validate(raw)
            except ValidationError as exc:
                raise ConfigValidationError(str(exc), path=path) from exc
        return settings

    # ------------------------------------------------------------------ users

    def user_dirs(self) -> list[Path]:
        return sorted(d for d in self.users_dir.iterdir() if (d / PROFILE_FILE).exists()) if self.users_dir.is_dir() else []

    def load_user(self, user_dir: Path) -> UserDeclaration:
        """One user's profile and every source they declare; topic keys must exist in the topics file."""
        profile_path = user_dir / PROFILE_FILE
        try:
            user = User.model_validate(self.read(profile_path))
        except ValidationError as exc:
            raise ConfigValidationError(str(exc), path=profile_path) from exc
        if user.id != user_dir.name:
            raise ConfigError(f"profile id {user.id!r} must match its folder name {user_dir.name!r}", path=profile_path)

        specs: list[SourceSpec] = []
        for path in sorted((user_dir / USER_SOURCES_DIR).glob("*.yaml")):
            specs.extend(self.load_specs(path))
        try:
            return UserDeclaration(user=user, sources=specs)
        except ValidationError as exc:
            raise ConfigValidationError(str(exc), path=user_dir) from exc

    def load_specs(self, path: Path) -> list[SourceSpec]:
        raw = self.read(path) or {}
        if not isinstance(raw, dict) or not isinstance(raw.get("sources"), list):
            raise ConfigValidationError("expected a top-level `sources:` list", path=path)
        try:
            return [source_spec_adapter.validate_python(item, context={"topics": self.topics}) for item in raw["sources"]]
        except ValidationError as exc:
            raise ConfigValidationError(str(exc), path=path) from exc

    @cached_property
    def users(self) -> dict[str, UserDeclaration]:
        """Every declared user, keyed by id."""
        return {d.user.id: d for d in (self.load_user(u) for u in self.user_dirs())}

    def get_user(self, user_id: str) -> UserDeclaration:
        try:
            return self.users[user_id]
        except KeyError:
            raise UnknownUserError(f"unknown user {user_id!r}; choose from {sorted(self.users)}") from None
