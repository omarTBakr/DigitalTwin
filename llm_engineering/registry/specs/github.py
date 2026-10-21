from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field

from llm_engineering.registry.keys import github_user_key
from llm_engineering.registry.specs.base import BaseSourceSpec


class RepoTopicRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    repo: str  # fnmatch glob on the repo name
    topic: str


class GitHubSpec(BaseSourceSpec):
    """All repos of one GitHub account (the user's own code and docs)."""

    provider: ClassVar[str] = "github"
    owned: ClassVar[bool] = True

    type: Literal["github"]
    username: str
    repos: list[str] = Field(default_factory=list)  # empty = every repo the account owns
    exclude_repos: list[str] = Field(default_factory=list)
    include_forks: bool = False
    include: list[str] = ["README*", "*.md", "*.py", "*.ipynb"]
    exclude: list[str] = Field(default_factory=list)
    skip_hidden: bool = True
    max_file_kb: int = Field(1024, gt=0)
    min_chars: int = Field(40, ge=0)
    topic_rules: list[RepoTopicRule] = Field(default_factory=list)

    def key(self, user_id: str) -> str:
        return github_user_key(self.username)

    def referenced_topics(self) -> set[str]:
        return {r.topic for r in self.topic_rules}
