import logging

from langchain_community.document_loaders import AsyncHtmlLoader
from langchain_community.document_transformers import Html2TextTransformer
from langchain_core.documents import Document

from llm_engineering.exceptions import ParseError, SourceUnavailableError
from llm_engineering.raw_data.crawlers.crawled_article import CrawledArticle

log = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
)
CRAWLER_NAME = "custom_article_crawler"


class CustomArticleCrawler:
    """Generic article crawler: plain HTTP fetch (LangChain AsyncHtmlLoader) + Html2TextTransformer.

    Works for most static blogs/docs. Used as a fallback when a site-specific crawler fails, and by the
    `articles` provider. No JavaScript, so pages that render client-side may come back thin.
    """

    def __init__(self, *, source: str, min_chars: int = 200):
        self.source = source
        self.min_chars = min_chars
        self._transformer = Html2TextTransformer(ignore_links=True, ignore_images=True)

    def crawl(self, url: str) -> CrawledArticle:
        """Raises SourceUnavailableError if the page can't be fetched, ParseError if it has no usable text."""
        return self.to_article(self._fetch(url))

    def _fetch(self, url: str) -> Document:
        loader = AsyncHtmlLoader(
            [url], header_template={"User-Agent": USER_AGENT}, raise_for_status=True, requests_per_second=1
        )
        try:
            docs = loader.load()
        except Exception as exc:  # aiohttp/asyncio errors vary; all mean "couldn't fetch"
            raise SourceUnavailableError(f"{url}: {exc}", source=self.source) from exc
        if not docs or not docs[0].page_content.strip():
            raise SourceUnavailableError(f"{url}: empty response", source=self.source)
        return docs[0]

    def to_article(self, html_doc: Document) -> CrawledArticle:
        """LangChain HTML Document -> CrawledArticle (no network)."""
        url = html_doc.metadata.get("source", "")
        text = self._transformer.transform_documents([html_doc])[0].page_content.strip()
        if len(text) < self.min_chars:
            raise ParseError(f"only {len(text)} characters of text", source=self.source, item=url)
        return CrawledArticle(
            url=url,
            title=html_doc.metadata.get("title"),
            content=text,
            metadata={
                "description": html_doc.metadata.get("description"),
                "language": html_doc.metadata.get("language"),
                "crawler": CRAWLER_NAME,
            },
        )
