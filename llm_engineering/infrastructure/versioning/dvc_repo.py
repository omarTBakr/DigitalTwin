import sys
from pathlib import Path

import yaml

from llm_engineering.exceptions import VersioningError
from llm_engineering.infrastructure.versioning.command import run_command
from llm_engineering.settings.paths import PROJECT_ROOT


class DvcRepo:
    """The DVC CLI for one repo (run through this interpreter, so the project's dvc version is used)."""

    def __init__(self, root: Path = PROJECT_ROOT):
        self.root = root

    def _dvc(self, *args: str) -> str:
        return run_command([sys.executable, "-m", "dvc", *args], cwd=self.root).stdout

    def add(self, path: Path) -> Path:
        """Track `path`; returns its pointer file (<path>.dvc)."""
        self._dvc("add", str(path))
        return path.with_name(path.name + ".dvc")

    def push(self, remote: str | None = None) -> None:
        self._dvc("push", *(["--remote", remote] if remote else []))

    def tracked_hash(self, pointer: Path) -> str:
        """The md5 recorded in a .dvc pointer file (identifies the data version)."""
        try:
            outs = yaml.safe_load((self.root / pointer).read_text(encoding="utf-8"))["outs"]
            return outs[0]["md5"]
        except (OSError, KeyError, IndexError, TypeError, yaml.YAMLError) as exc:
            raise VersioningError(f"cannot read {pointer}: {exc}") from exc
