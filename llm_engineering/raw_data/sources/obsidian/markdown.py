"""Obsidian-flavoured markdown: wikilinks, embeds, code fences."""

import re

EMBED = re.compile(r"!\[\[[^\]]*\]\]")
WIKILINK = re.compile(r"\[\[([^\]|#]*)(?:#[^\]|]*)?(?:\|([^\]]*))?\]\]")
CODE_FENCE = re.compile(r"```.*?```", re.S)


def clean_obsidian_markdown(text: str) -> str:
    """Drop ![[embeds]]; [[target|alias]] -> alias, [[target#heading]] -> target."""
    text = EMBED.sub("", text)
    text = WIKILINK.sub(lambda m: (m.group(2) or m.group(1)).strip(), text)
    return text.strip()


def strip_code_fences(text: str) -> str:
    return CODE_FENCE.sub("", text)
