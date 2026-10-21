import subprocess
from pathlib import Path

from llm_engineering.exceptions import VersioningError


def run_command(args: list[str], cwd: Path, *, ok_codes: tuple[int, ...] = (0,)) -> subprocess.CompletedProcess:
    """Run a CLI command; a missing binary or an unexpected exit code becomes VersioningError."""
    try:
        result = subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=False)
    except OSError as exc:
        raise VersioningError(f"cannot run {args[0]}: {exc}") from exc
    if result.returncode not in ok_codes:
        detail = (result.stderr or result.stdout).strip()
        raise VersioningError(f"`{' '.join(args)}` exited {result.returncode}: {detail}")
    return result
