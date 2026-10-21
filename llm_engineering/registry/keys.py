"""Canonical source keys: two declarations of the same thing must produce the same key."""

from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

TRACKING_PREFIXES = ("utm_", "mc_")
TRACKING_NAMES = {"fbclid", "gclid", "ref", "source"}  # source/ref: Medium & co. tracking


def normalize_url(url: str) -> str:
    """Lowercase scheme/host, drop fragment, tracking params and trailing '/', sort the query."""
    parts = urlsplit(url.strip())
    query = sorted(
        (k, v)
        for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if not k.lower().startswith(TRACKING_PREFIXES) and k.lower() not in TRACKING_NAMES
    )
    path = parts.path.rstrip("/") or ""
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, urlencode(query), ""))


def slug(value: str) -> str:
    return value.strip().lower()


def medium_tag_key(tag: str) -> str:
    return f"medium:tag:{slug(tag)}"


def medium_author_key(handle: str) -> str:
    return f"medium:author:@{slug(handle).lstrip('@')}"


def article_key(url: str) -> str:
    return f"article:{normalize_url(url)}"


def github_user_key(username: str) -> str:
    return f"github:user:{slug(username)}"


def obsidian_key(user_id: str, vault_path: Path) -> str:
    return f"obsidian:{user_id}:{vault_path.resolve().as_posix()}"


def linkedin_key(user_id: str) -> str:
    return f"linkedin:{user_id}"


def subscription_key(user_id: str, source_id: str) -> str:
    return f"{user_id}|{source_id}"
