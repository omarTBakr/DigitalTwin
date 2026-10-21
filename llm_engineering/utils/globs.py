from collections.abc import Iterable
from fnmatch import fnmatch
from pathlib import PurePosixPath


def matches_any(path: str, patterns: Iterable[str]) -> bool:
    """fnmatch against several globs; '*' also crosses '/' (so 'copilot/*' covers subfolders)."""
    return any(fnmatch(path, p) for p in patterns)


def has_hidden_part(path: str) -> bool:
    """True if any component of a POSIX path starts with '.' (e.g. '.github/x.md')."""
    return any(part.startswith(".") for part in PurePosixPath(path).parts)
