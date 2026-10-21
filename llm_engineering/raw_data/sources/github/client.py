import email.utils
import time
from types import TracebackType
from urllib.parse import quote

import httpx

from llm_engineering.exceptions import (
    AuthenticationError,
    RateLimitError,
    SourceUnavailableError,
)
from llm_engineering.utils.dates import utc_now

API = "https://api.github.com"
RAW = "https://raw.githubusercontent.com"



def _parse_retry_after(resp: httpx.Response) -> float | None:
    """Seconds to wait from a Retry-After header (delta-seconds or HTTP date), or None."""
    value = resp.headers.get("Retry-After")
    if not value:
        return None
    if value.isdigit():
        return float(value)
    try:
        when = email.utils.parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    return max((when - utc_now()).total_seconds(), 0)

class GitHubClient:
    """Thin GitHub REST + raw-content client; HTTP failures become project exceptions."""

    def __init__(self, *, source: str, token: str | None = None):
        self.source = source
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "DigitalTwinCrawler/0.1"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self._http = httpx.Client(headers=headers, follow_redirects=True, timeout=30)

    def __enter__(self) -> "GitHubClient":
        return self

    def __exit__(
        self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: TracebackType | None
    ) -> None:
        self._http.close()

    def _get(self, url: str, params: dict | None = None) -> httpx.Response:
        try:
            resp = self._http.get(url, params=params)
        except httpx.HTTPError as exc:
            raise SourceUnavailableError(f"{url}: {exc}", source=self.source) from exc

        if resp.status_code == 401:
            raise AuthenticationError("GITHUB_TOKEN was rejected; check .env", source=self.source)
        if resp.status_code in (403, 429) and resp.headers.get("X-RateLimit-Remaining") == "0":
            reset = int(resp.headers.get("X-RateLimit-Reset", "0"))
            raise RateLimitError(
                "API rate limit hit; set GITHUB_TOKEN in .env for 5000 requests/hour",
                source=self.source,
                retry_after=_parse_retry_after(resp) or max(reset - time.time(), 0),
            )
        if resp.status_code >= 400:
            raise SourceUnavailableError(f"{url}: HTTP {resp.status_code}", source=self.source)
        return resp

    def user_repos(self, username: str) -> list[dict]:
        repos: list[dict] = []
        page = 1
        while True:
            batch = self._get(
                f"{API}/users/{username}/repos", {"type": "owner", "per_page": 100, "page": page}
            ).json()
            repos.extend(batch)
            if len(batch) < 100:
                return repos
            page += 1

    def repo_tree(self, repo: dict) -> dict:
        """Recursive file tree of the default branch: {"tree": [{"path", "type", "size"}, ...], "truncated"}."""
        url = f"{API}/repos/{repo['full_name']}/git/trees/{quote(repo['default_branch'])}"
        return self._get(url, {"recursive": "1"}).json()

    def raw_file(self, repo: dict, path: str) -> str:
        return self._get(f"{RAW}/{repo['full_name']}/{quote(repo['default_branch'])}/{quote(path)}").text

    def rate_limit_remaining(self) -> int:
        return self._get(f"{API}/rate_limit").json()["resources"]["core"]["remaining"]
