import json
import os
from collections.abc import Iterable
from pathlib import Path

from pydantic import BaseModel

from llm_engineering.exceptions import StorageError
from llm_engineering.raw_data.store.base import RawDataStore
from llm_engineering.registry.store.base import RegistryStore

# Provenance (collected_at, run_id) changes on every crawl even when content doesn't; leaving it out
# keeps snapshots stable, so a new DVC version means the data really changed. It stays in the store.
SNAPSHOT_EXCLUDE = {"provenance"}
REGISTRY_DIR = "registry"


class RawDataSnapshotExporter:
    """Writes the stores to JSONL for DVC: `<out_dir>/<provider>.jsonl` (documents) and
    `<out_dir>/registry/{users,sources,subscriptions}.jsonl`. One record per line, sorted by id,
    keys sorted — deterministic output that DVC can version and diff."""

    def __init__(self, store: RawDataStore, registry: RegistryStore, out_dir: Path):
        self.store = store
        self.registry = registry
        self.out_dir = out_dir

    def export(self, providers: list[str]) -> dict[str, int]:
        """Returns the number of records written per file stem."""
        written: dict[str, int] = {}
        for provider in providers:
            docs = sorted(self.store.find(provider), key=lambda d: d.id)
            written[provider] = self._write(self.out_dir / f"{provider}.jsonl", docs, SNAPSHOT_EXCLUDE)

        registry_dir = self.out_dir / REGISTRY_DIR
        written["users"] = self._write(registry_dir / "users.jsonl", sorted(self.registry.users(), key=lambda u: u.id))
        # source state changes every run; versioning the declarations only keeps diffs meaningful
        sources = sorted(self.registry.sources(), key=lambda s: s.id)
        written["sources"] = self._write(registry_dir / "sources.jsonl", sources, {"state"})
        subs = sorted(self.registry.subscriptions(), key=lambda s: (s.user_id, s.source_id))
        written["subscriptions"] = self._write(registry_dir / "subscriptions.jsonl", subs)
        return written

    @staticmethod
    def _write(path: Path, records: Iterable[BaseModel], exclude: set[str] | None = None) -> int:
        lines = [json.dumps(r.model_dump(mode="json", exclude=exclude), sort_keys=True, ensure_ascii=False) for r in records]
        tmp = path.with_suffix(".jsonl.tmp")
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp.write_text("".join(line + "\n" for line in lines), encoding="utf-8")
            os.replace(tmp, path)  # atomic: DVC never sees a half-written file
        except OSError as exc:
            raise StorageError(f"cannot write snapshot {path}: {exc}") from exc
        return len(lines)
