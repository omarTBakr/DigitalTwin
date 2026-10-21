from collections import defaultdict

from llm_engineering.exceptions import UnknownSourceError, UnknownUserError
from llm_engineering.registry.store.base import RegistryStore


class SourceSelector:
    """Decides which sources a pipeline run crawls.

    no arguments      → every enabled source
    user_id           → the enabled sources that user subscribes to
    source_ids        → exactly those (what a trigger passes); with user_id they must be subscribed
    """

    def __init__(self, store: RegistryStore):
        self.store = store

    def select(self, user_id: str | None = None, source_ids: list[str] | None = None) -> dict[str, list[str]]:
        """Returns {provider: [source_id, ...]}, sorted."""
        allowed: set[str] | None = None
        if user_id is not None:
            if user_id not in {u.id for u in self.store.users()}:
                raise UnknownUserError(f"unknown user {user_id!r}")
            allowed = {s.source_id for s in self.store.subscriptions(user_id)}

        if source_ids:
            found = {s.id: s for s in self.store.sources(source_ids)}
            missing = sorted(set(source_ids) - set(found))
            if missing:
                raise UnknownSourceError(f"unknown sources {missing}")
            if allowed is not None and (outside := sorted(set(source_ids) - allowed)):
                raise UnknownSourceError(f"user {user_id!r} is not subscribed to {outside}")
            sources = list(found.values())
        else:
            sources = self.store.sources(allowed) if allowed is not None else self.store.sources()

        selection: dict[str, list[str]] = defaultdict(list)
        for source in sources:
            if source.enabled:
                selection[source.provider].append(source.id)
        return {provider: sorted(ids) for provider, ids in sorted(selection.items())}
