from dataclasses import dataclass

from llm_engineering.registry.models.source import Source
from llm_engineering.registry.models.user_declaration import UserDeclaration
from llm_engineering.registry.store.base import RegistryStore


@dataclass
class SeedStats:
    users: int = 0
    sources_declared: int = 0
    sources_new: int = 0
    subscriptions_new: int = 0


class RegistrySeeder:
    """Writes user declarations into the registry. Idempotent: re-running changes nothing new.

    The same source declared by several users is stored once (canonical id) with one subscription each.
    """

    def __init__(self, store: RegistryStore):
        self.store = store

    def seed(self, declarations: list[UserDeclaration]) -> SeedStats:
        stats = SeedStats()
        self.store.setup()
        for declaration in declarations:
            user = declaration.user
            self.store.upsert_user(user)
            stats.users += 1
            for spec in declaration.sources:
                source = Source.from_spec(spec, user.id)
                stats.sources_declared += 1
                stats.sources_new += self.store.upsert_source(source)
                stats.subscriptions_new += self.store.subscribe(user.id, source.id)
        return stats
