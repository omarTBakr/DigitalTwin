"""Which repos and files to collect, and how to classify them."""

from pathlib import PurePosixPath

from llm_engineering.registry.specs.github import GitHubSpec
from llm_engineering.utils.globs import has_hidden_part, matches_any

DOC_SUFFIXES = {".md", ".markdown", ".rst", ".txt", ""}


def select_repos(repos: list[dict], cfg: GitHubSpec) -> list[dict]:
    return [
        repo
        for repo in repos
        if (not cfg.repos or matches_any(repo["name"], cfg.repos))
        and not matches_any(repo["name"], cfg.exclude_repos)
        and (cfg.include_forks or not repo.get("fork"))
    ]


def is_wanted(path: str, size: int, cfg: GitHubSpec) -> bool:
    if cfg.skip_hidden and has_hidden_part(path):
        return False
    if size > cfg.max_file_kb * 1024:
        return False
    name = PurePosixPath(path).name
    if not (matches_any(name, cfg.include) or matches_any(path, cfg.include)):
        return False
    return not matches_any(path, cfg.exclude)


def select_files(tree: dict, cfg: GitHubSpec) -> list[str]:
    return [
        item["path"]
        for item in tree.get("tree", [])
        if item["type"] == "blob" and is_wanted(item["path"], item.get("size", 0), cfg)
    ]


def file_type(path: str) -> str:
    """docs | code | notebook — lets later steps treat prose and code differently."""
    suffix = PurePosixPath(path).suffix.lower()
    if suffix == ".ipynb":
        return "notebook"
    return "docs" if suffix in DOC_SUFFIXES else "code"
