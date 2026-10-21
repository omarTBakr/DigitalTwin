from typing import get_args

from llm_engineering.exceptions import ConfigValidationError
from llm_engineering.raw_data.store.base import RawDataStore
from llm_engineering.settings.app_settings import StoreBackend, get_settings


def create_raw_data_store(backend: str | None = None) -> RawDataStore:
    """The configured RawDataStore. `backend` overrides RAW_STORE_BACKEND."""
    backend = backend or get_settings().raw_store.backend
    if backend not in get_args(StoreBackend):
        raise ConfigValidationError(f"unknown raw data store backend {backend!r}; choose from {get_args(StoreBackend)}")

    if backend == "mongo":
        from llm_engineering.raw_data.store.mongo_store import (
            MongoRawDataStore,  # driver only when used
        )

        return MongoRawDataStore()
    raise ConfigValidationError(f"no RawDataStore implementation for backend {backend!r}")
