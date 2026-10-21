from dataclasses import asdict
from typing import Annotated

from zenml import step

from llm_engineering.crawl_config.yaml_loader import YamlLoader
from llm_engineering.registry.seeder import RegistrySeeder
from llm_engineering.registry.store.factory import create_registry_store
from steps.etl.zenml_helpers import log_summary


@step
def sync_registry() -> Annotated[dict[str, int], "registry_sync"]:
    """Seed the registry from configs/users/*: users, sources (deduplicated by canonical key), subscriptions.

    Idempotent; existing sources keep their crawl state. (A UI will later write to the same registry.)
    """
    stats = asdict(RegistrySeeder(create_registry_store()).seed(list(YamlLoader().users.values())))
    log_summary(stats)
    return stats
