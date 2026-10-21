from collections import Counter
from dataclasses import dataclass, field

from llm_engineering.registry.models.user import User
from llm_engineering.topics.matcher import TopicMatcher
from llm_engineering.topics.models import Topic


@dataclass
class CrawlContext:
    """Run-wide inputs every extractor receives."""

    run_id: str
    topics: dict[str, Topic]
    users: dict[str, User] = field(default_factory=dict)  # owners of self sources (author names)
    existing_topics: dict[str, set[str]] = field(default_factory=dict)  # stored doc id -> its topics

    def __post_init__(self) -> None:
        self.matcher = TopicMatcher(self.topics)

    def topic_counts(self) -> Counter[str]:
        return Counter(t for topics in self.existing_topics.values() for t in topics)

    def owner_name(self, owner_id: str | None) -> str:
        user = self.users.get(owner_id or "")
        return user.name if user else (owner_id or "unknown")
