import time
from collections.abc import Iterator
from contextlib import contextmanager
from typing import ClassVar
from urllib.parse import quote

from llm_engineering.exceptions import AuthenticationError, RateLimitError, SourceError
from llm_engineering.raw_data.documents.raw_document import RawDocument
from llm_engineering.raw_data.sources.base.extractor import BaseExtractor
from llm_engineering.raw_data.sources.base.health import SourceHealth
from llm_engineering.raw_data.sources.github.client import GitHubClient
from llm_engineering.raw_data.sources.github.files import (
    file_type,
    select_files,
    select_repos,
)
from llm_engineering.raw_data.sources.github.notebook import notebook_to_markdown
from llm_engineering.raw_data.sources.github.settings import GitHubSettings
from llm_engineering.registry.models.source import Source
from llm_engineering.registry.specs.github import GitHubSpec
from llm_engineering.settings.app_settings import get_settings
from llm_engineering.utils.dates import parse_iso_datetime
from llm_engineering.utils.globs import matches_any


class GitHubExtractor(BaseExtractor[GitHubSettings]):
    """GitHub accounts: one document per README / markdown / Python / notebook file of each repo.

    Auth and rate-limit errors stop the provider; a repo or file that fails is recorded and skipped.
    """

    provider: ClassVar[str] = "github"

    @staticmethod
    def _client() -> GitHubClient:
        token = get_settings().github.token
        return GitHubClient(source="github", token=token.get_secret_value() if token else None)

    @contextmanager
    def session(self):
        with self._client() as client:
            self.client = client
            yield

    def extract_source(self, source: Source) -> Iterator[RawDocument]:
        spec: GitHubSpec = source.typed_spec
        repos = select_repos(self.client.user_repos(spec.username), spec)
        self.log.info("%s: %d repos selected", spec.username, len(repos))
        for repo in repos:
            try:
                yield from self._repo_documents(source, spec, repo)
            except (AuthenticationError, RateLimitError):
                raise
            except SourceError as exc:
                self.log.warning("%s: skipped (%s)", repo["name"], exc)
                self.record_failed(repo["html_url"], f"repo skipped: {exc}")

    def _repo_documents(self, source: Source, spec: GitHubSpec, repo: dict) -> Iterator[RawDocument]:
        tree = self.client.repo_tree(repo)
        if tree.get("truncated"):
            self.log.warning("%s: file tree truncated by GitHub; some files will be missing", repo["name"])
        paths = select_files(tree, spec)
        topics = self._repo_topics(spec, repo)
        kept = 0
        for path in paths:
            time.sleep(self.settings.request_delay_s)
            text = self._file_text(repo, path)
            if text is None:
                continue
            if len(text) < spec.min_chars:
                self.record_skipped(f"{repo['name']}/{path}", f"shorter than {spec.min_chars} chars")
                continue
            kept += 1
            yield self.make_document(
                source=source,
                id=f"github:{repo['full_name']}/{path}",
                kind="github",
                origin="self",
                content=text,
                author=self.context.owner_name(source.owner_id),
                query=repo["name"],
                topics=topics,
                title=f"{repo['name']}/{path}",
                url=f"{repo['html_url']}/blob/{repo['default_branch']}/{quote(path)}",
                created_at=parse_iso_datetime(repo.get("created_at")),
                updated_at=parse_iso_datetime(repo.get("pushed_at")),
                metadata={
                    "repo": repo["name"],
                    "path": path,
                    "file_type": file_type(path),
                    "language": repo.get("language"),
                    "repo_topics": repo.get("topics") or [],
                    "repo_description": repo.get("description"),
                },
            )
        self.log.info("%s: %d files matched, %d kept", repo["name"], len(paths), kept)

    def _file_text(self, repo: dict, path: str) -> str | None:
        """File content as text (notebooks converted), or None if it can't be fetched or read."""
        try:
            text = self.client.raw_file(repo, path)
            if file_type(path) == "notebook":
                text = notebook_to_markdown(text)
        except (AuthenticationError, RateLimitError):
            raise
        except (SourceError, ValueError) as exc:
            self.log.warning("%s/%s: %s", repo["name"], path, exc)
            self.record_failed(f"{repo['name']}/{path}", str(exc))
            return None
        return text.strip()

    def _repo_topics(self, spec: GitHubSpec, repo: dict) -> set[str]:
        tags = list(repo.get("topics") or [])
        if language := repo.get("language"):
            tags.append(language.replace("+", "plus"))  # "C++" -> "Cplusplus" so it can match "cplusplus"
        topics = self.context.matcher.from_tags(tags)
        topics |= {r.topic for r in spec.topic_rules if matches_any(repo["name"], [r.repo])}
        return topics

    def health_check(self, *, offline: bool = False) -> SourceHealth:
        usernames = [s.typed_spec.username for s in self.sources]
        if offline:
            return self.health(True, f"accounts {usernames} (network check skipped)")
        token = get_settings().github.token
        repos: dict[str, list[str]] = {}
        try:
            with self._client() as client:
                for source in self.sources:
                    spec: GitHubSpec = source.typed_spec
                    repos[spec.username] = [r["name"] for r in select_repos(client.user_repos(spec.username), spec)]
                remaining = client.rate_limit_remaining()
        except SourceError as exc:
            return self.health(False, str(exc))
        summary = ", ".join(f"{u}: {len(r)} repos" for u, r in repos.items())
        return self.health(
            True, f"{summary} (token: {'yes' if token else 'no'}, API calls left: {remaining})",
            repos=repos, api_remaining=remaining,
        )
