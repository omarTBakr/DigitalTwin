from pathlib import Path

from llm_engineering.infrastructure.versioning.command import run_command
from llm_engineering.settings.paths import PROJECT_ROOT


class GitRepo:
    """Minimal git operations, always limited to explicit paths (never commits unrelated changes)."""

    def __init__(self, root: Path = PROJECT_ROOT):
        self.root = root

    def _git(self, *args: str, ok_codes: tuple[int, ...] = (0,)):
        return run_command(["git", *args], cwd=self.root, ok_codes=ok_codes)

    def commit_paths(self, paths: list[Path], message: str) -> str | None:
        """Stage and commit only `paths`. Returns the new commit sha, or None if nothing changed."""
        existing = [str(p) for p in paths if (self.root / p).exists()]
        if not existing:
            return None
        self._git("add", "--", *existing)
        # exit 1 = staged differences exist for these paths, 0 = nothing to commit
        if self._git("diff", "--cached", "--quiet", "--", *existing, ok_codes=(0, 1)).returncode == 0:
            return None
        self._git("commit", "-m", message, "--", *existing)
        return self._git("rev-parse", "HEAD").stdout.strip()
