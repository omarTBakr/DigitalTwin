"""Obsidian-flavoured markdown: wikilinks, embeds, tags."""

import re

EMBED = re.compile(r"!\[\[[^\]]*\]\]")
WIKILINK = re.compile(r"\[\[([^\]|#]*)(?:#[^\]|]*)?(?:\|([^\]]*))?\]\]")
CODE_FENCE = re.compile(r"```.*?```", re.S)
# Obsidian tags start a line or follow whitespace; "(#the-problem)" anchor links are not tags.
INLINE_TAG = re.compile(r"(?:^|(?<=\s))#([A-Za-z][\w/-]*)", re.M)


def clean_obsidian_markdown(text: str) -> str:
    """Drop ![[embeds]]; [[target|alias]] -> alias, [[target#heading]] -> target."""
    text = EMBED.sub("", text)
    text = WIKILINK.sub(lambda m: (m.group(2) or m.group(1)).strip(), text)
    return text.strip()


def note_tags(metadata: dict, body: str) -> list[str]:
    """Frontmatter `tags` + inline #tags (code blocks ignored, so '#include' isn't a tag)."""
    raw = metadata.get("tags") or []
    tags = [raw] if isinstance(raw, str) else [str(t) for t in raw]
    tags += INLINE_TAG.findall(CODE_FENCE.sub("", body))
    return [t.strip("#") for t in tags if t]
