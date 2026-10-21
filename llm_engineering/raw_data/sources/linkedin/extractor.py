from collections.abc import Callable, Iterator
from typing import ClassVar

from llm_engineering.exceptions import ParseError, SourceUnavailableError
from llm_engineering.raw_data.documents.raw_document import RawDocument
from llm_engineering.raw_data.sources.base.extractor import BaseExtractor
from llm_engineering.raw_data.sources.base.health import SourceHealth
from llm_engineering.raw_data.sources.linkedin.export_files import (
    COMMENTS_CSV,
    SHARES_CSV,
    LinkedInExport,
)
from llm_engineering.raw_data.sources.linkedin.parsers import (
    LinkedInItem,
    parse_article,
    parse_comment,
    parse_post,
)
from llm_engineering.raw_data.sources.linkedin.settings import LinkedInSettings
from llm_engineering.registry.models.source import Source
from llm_engineering.registry.specs.linkedin import LinkedInExportSpec

EXPORT_HELP = (
    "LinkedIn export not found in {}. Request it at LinkedIn → Settings → Data privacy → "
    "Get a copy of your data, then unzip it there."
)


class LinkedInExportExtractor(BaseExtractor[LinkedInSettings]):
    """Each user's own posts, comments and articles from their official LinkedIn data export."""

    provider: ClassVar[str] = "linkedin"

    @staticmethod
    def export(source: Source) -> LinkedInExport:
        spec: LinkedInExportSpec = source.typed_spec
        return LinkedInExport(spec.export_dir, source=source.id)

    def extract_source(self, source: Source) -> Iterator[RawDocument]:
        spec: LinkedInExportSpec = source.typed_spec
        export = self.export(source)
        if not export.exists():
            raise SourceUnavailableError(EXPORT_HELP.format(export.root), source=source.id)

        if "posts" in spec.include:
            yield from self._from_csv(source, export, SHARES_CSV, parse_post)
        if "comments" in spec.include:
            yield from self._from_csv(source, export, COMMENTS_CSV, parse_comment)
        if "articles" in spec.include:
            for path in export.article_files():
                try:
                    item = parse_article(export.read_text(path), path)
                except ParseError as exc:
                    self.log.warning("%s", exc)
                    self.record_failed(path.name, str(exc))
                    continue
                if doc := self._document(source, item):
                    yield doc

    def _from_csv(
        self, source: Source, export: LinkedInExport, filename: str, parse: Callable[[dict[str, str]], LinkedInItem]
    ) -> Iterator[RawDocument]:
        path = export.find(filename)
        if path is None:
            self.log.warning("%s not found in %s", filename, export.root)
            return
        try:
            for row in export.read_csv(path):
                if doc := self._document(source, parse(row)):
                    yield doc
        except ParseError as exc:
            self.log.warning("skipping %s: %s", filename, exc)
            self.record_failed(filename, str(exc))

    def _document(self, source: Source, item: LinkedInItem) -> RawDocument | None:
        spec: LinkedInExportSpec = source.typed_spec
        if len(item.text) < spec.min_chars:
            self.record_skipped(item.url or f"{item.kind}:{item.native_id}", f"shorter than {spec.min_chars} chars")
            return None
        return self.make_document(
            source=source,
            id=f"{item.kind}:{source.owner_id}:{item.native_id}",
            kind=item.kind,
            origin="self",
            content=item.text,
            author=self.context.owner_name(source.owner_id),
            query=item.kind,
            topics=self.context.matcher.from_tags(item.hashtags),
            title=item.title,
            url=item.url,
            created_at=item.created_at,
            metadata=item.metadata,
        )

    def health_check(self, *, offline: bool = False) -> SourceHealth:
        details: dict[str, dict] = {}
        for source in self.sources:
            export = self.export(source)
            if not export.exists():
                return self.health(False, f"{source.id}: " + EXPORT_HELP.format(export.root))
            files = {name: export.find(name) is not None for name in (SHARES_CSV, COMMENTS_CSV)}
            details[source.id] = {"files": files, "articles": len(export.article_files())}
        ok = all(any(d["files"].values()) or d["articles"] for d in details.values())
        return self.health(ok, f"{len(details)} export(s): {details}", exports=details)
