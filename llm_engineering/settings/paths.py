"""Every filesystem location the project uses, anchored at the repo root (works from any cwd)."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]  # llm_engineering/settings/paths.py -> repo root


def from_root(path: Path) -> Path:
    """Resolve a config-supplied relative path against the repo root; absolute paths pass through."""
    path = path.expanduser()
    return path if path.is_absolute() else PROJECT_ROOT / path


# ---- YAML configuration
CONFIG_DIR = PROJECT_ROOT / "configs"
TOPICS_FILE = CONFIG_DIR / "topics.yaml"
PROVIDERS_DIR = CONFIG_DIR / "providers"  # crawler tuning per provider: <provider>.yaml
USERS_DIR = CONFIG_DIR / "users"  # one folder per user: profile.yaml + sources/*.yaml

# ---- settings / secrets (git-ignored; template in .env.example)
ENV_FILE = PROJECT_ROOT / ".env"

# ---- data
DATA_DIR = PROJECT_ROOT / "data"
RAW_SNAPSHOT_DIR = DATA_DIR / "raw"  # DVC-versioned JSONL snapshots of the raw data store
EXPORTS_DIR = DATA_DIR / "exports"  # manual downloads, e.g. the LinkedIn export
MANIFESTS_DIR = DATA_DIR / "manifests"
SOURCE_HEALTH_FILE = MANIFESTS_DIR / "source_health.json"

# ---- DVC setup files, committed together with the data pointer
DVC_SETUP_FILES = [PROJECT_ROOT / ".dvc" / "config", PROJECT_ROOT / ".dvc" / ".gitignore", PROJECT_ROOT / ".dvcignore"]
