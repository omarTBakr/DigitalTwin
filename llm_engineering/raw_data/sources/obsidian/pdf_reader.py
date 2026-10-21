from dataclasses import dataclass
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader

from llm_engineering.exceptions import ParseError

PAGE_BREAK = "\n\n"


@dataclass
class PdfText:
    text: str  # all pages, in order
    pages: int
    title: str | None = None
    author: str | None = None


def read_pdf(path: Path, *, source: str) -> PdfText:
    """Extract a PDF's text page by page with LangChain's PyPDFLoader (pypdf, BSD-licensed).

    Raises ParseError if the file can't be read (encrypted, corrupt) or has no extractable text
    (scanned images would need OCR).
    """
    try:
        pages = PyPDFLoader(str(path)).load()
    except Exception as exc:  # pypdf raises many types for broken files
        raise ParseError(f"unreadable PDF: {exc}", source=source, item=path.name) from exc
    text = PAGE_BREAK.join(p.page_content.strip() for p in pages if p.page_content.strip())
    if not text:
        raise ParseError("no extractable text (scanned PDF?)", source=source, item=path.name)
    meta = pages[0].metadata if pages else {}
    return PdfText(text=text, pages=len(pages), title=meta.get("title") or None, author=meta.get("author") or None)
