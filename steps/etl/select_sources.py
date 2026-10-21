from typing import Annotated

from zenml import step

from llm_engineering.registry.selector import SourceSelector
from llm_engineering.registry.store.factory import create_registry_store
from steps.etl.zenml_helpers import log_summary


@step
def select_sources(
    registry_sync: dict[str, int],
    user_id: str | None = None,
    source_ids: list[str] | None = None,
) -> Annotated[dict[str, list[str]], "selection"]:
    """Which registered sources this run crawls: all, one user's, or exactly `source_ids` (triggers).

    `registry_sync` is only an ordering dependency: select after the registry is up to date.
    """
    selection = SourceSelector(create_registry_store()).select(user_id=user_id, source_ids=source_ids)
    log_summary({"user_id": user_id or "all", "sources": {p: len(ids) for p, ids in selection.items()}})
    return selection
