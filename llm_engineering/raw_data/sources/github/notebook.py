import json


def notebook_to_markdown(raw: str) -> str:
    """Jupyter .ipynb JSON -> markdown: markdown cells as-is, code cells fenced, outputs dropped.

    Raises ValueError if the notebook can't be read.
    """
    try:
        nb = json.loads(raw)
        lang = nb.get("metadata", {}).get("language_info", {}).get("name", "python")
        chunks = []
        for cell in nb.get("cells", []):
            src = "".join(cell.get("source", [])).strip()
            if not src:
                continue
            if cell.get("cell_type") == "code":
                chunks.append(f"```{lang}\n{src}\n```")
            elif cell.get("cell_type") == "markdown":
                chunks.append(src)
    except (json.JSONDecodeError, AttributeError, TypeError) as exc:
        raise ValueError(f"unreadable notebook: {exc}") from exc
    return "\n\n".join(chunks)
