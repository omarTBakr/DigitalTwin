import hashlib


def content_hash(text: str) -> str:
    """Full sha256 of the text, for change detection and dedupe."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def short_id(*parts: str, length: int = 16) -> str:
    """Short, stable id derived from one or more strings."""
    return hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()[:length]
