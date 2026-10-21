from typing import Annotated, Any

from zenml import step

from llm_engineering.exceptions import StorageError, VersioningError
from llm_engineering.infrastructure.versioning.dvc_repo import DvcRepo
from llm_engineering.infrastructure.versioning.git_repo import GitRepo
from llm_engineering.raw_data.snapshot.exporter import RawDataSnapshotExporter
from llm_engineering.raw_data.sources.registry import PROVIDERS
from llm_engineering.raw_data.store.factory import create_raw_data_store
from llm_engineering.registry.store.factory import create_registry_store
from llm_engineering.settings.app_settings import get_settings
from llm_engineering.settings.paths import DVC_SETUP_FILES
from steps.etl.zenml_helpers import current_run_id, log_summary


@step
def version_raw_data(crawl_summaries: list[dict[str, Any]]) -> Annotated[dict[str, Any], "versioning_summary"]:
    """Snapshot documents (data/raw/<provider>.jsonl) and the registry (data/raw/registry/*.jsonl),
    `dvc add` them, commit the pointer files, `dvc push`.

    Runs after every crawl step (their summaries are its input). A failure here is reported, not raised,
    so the summary step still shows the crawl results; the store itself is never affected.
    """
    settings = get_settings().versioning
    if not settings.enabled:
        return {"status": "skipped"}

    summary: dict[str, Any] = {"status": "ok", "snapshot_dir": str(settings.snapshot_dir)}
    try:
        exporter = RawDataSnapshotExporter(create_raw_data_store(), create_registry_store(), settings.snapshot_dir)
        summary["records"] = exporter.export(sorted(PROVIDERS))

        dvc = DvcRepo()
        pointer = dvc.add(settings.snapshot_dir)
        summary["data_md5"] = dvc.tracked_hash(pointer)

        if settings.auto_commit:
            sources = ", ".join(f"{s['provider']}={s.get('stored_total', 0)}" for s in crawl_summaries)
            message = f"data: raw snapshot {current_run_id()}\n\n{sources}"
            # DVC setup files go in the same commit, so the pointer works from a fresh clone
            paths = [pointer, settings.snapshot_dir.parent / ".gitignore", *DVC_SETUP_FILES]
            summary["git_commit"] = GitRepo().commit_paths(paths, message) or "no changes"
        if settings.auto_push:
            dvc.push(settings.remote)
            summary["pushed"] = True
    except (VersioningError, StorageError) as exc:
        summary.update(status="failed", error=str(exc))

    log_summary(summary)
    return summary
