from collections.abc import Iterable

from llm_engineering.topics.models import Topic
from llm_engineering.utils.text import normalize_tag


class TopicMatcher:
    """Maps free-form tags (Medium tags, LinkedIn hashtags, GitHub topics, vault tags) to topic keys."""

    def __init__(self, topics: dict[str, Topic]):
        self._by_tag: dict[str, set[str]] = {}
        for key, topic in topics.items():
            for tag in [key, *topic.medium_tags]:
                self._by_tag.setdefault(normalize_tag(tag), set()).add(key)
        self._vault_prefixes = [
            (prefix.lower().strip("#/"), key) for key, topic in topics.items() for prefix in topic.obsidian_tags
        ]

    def from_tags(self, tags: Iterable[str]) -> set[str]:
        """Exact (normalized) match against each topic's key and `medium_tags`."""
        found: set[str] = set()
        for tag in tags:
            found |= self._by_tag.get(normalize_tag(tag), set())
        return found

    def from_vault_tags(self, tags: Iterable[str]) -> set[str]:
        """Prefix match against `obsidian_tags`: 'nlp' matches 'nlp/sequence-models'."""
        found: set[str] = set()
        for tag in tags:
            tag = tag.lower().strip("#/")
            for prefix, key in self._vault_prefixes:
                if tag == prefix or tag.startswith(prefix + "/"):
                    found.add(key)
        return found
