from bs4 import BeautifulSoup
from markdownify import markdownify


def html_to_markdown(html: str | BeautifulSoup) -> str:
    """HTML (string or parsed soup) to ATX-heading markdown."""
    return markdownify(str(html), heading_style="ATX").strip()


def normalize_tag(tag: str) -> str:
    """'#MachineLearning', 'machine-learning' and 'Machine Learning' all become 'machinelearning'."""
    return "".join(ch for ch in tag.lower().lstrip("#") if ch.isalnum())
