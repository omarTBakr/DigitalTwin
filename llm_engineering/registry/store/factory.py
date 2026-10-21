from typing import get_args

from llm_engineering.exceptions import ConfigValidationError
from llm_engineering.registry.store.base import RegistryStore
from llm_engineering.settings.app_settings import StoreBackend, get_settings


def create_registry_store(backend: str | None = None) -> RegistryStore:
    """The configured RegistryStore (same backend as the raw data store, RAW_STORE_BACKEND)."""
    backend = backend or get_settings().raw_store.backend
    if backend not in get_args(StoreBackend):
        raise ConfigValidationError(f"unknown store backend {backend!r}; choose from {get_args(StoreBackend)}")

    if backend == "mongo":
        from llm_engineering.registry.store.mongo_store import (
            MongoRegistryStore,  # driver only when used
        )

        return MongoRegistryStore()
    raise ConfigValidationError(f"no RegistryStore implementation for backend {backend!r}")
