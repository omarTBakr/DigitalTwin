from collections import Counter
from collections.abc import Iterator
from pathlib import Path
from typing import ClassVar

from llm_engineering.exceptions import ParseError, SourceUnavailableError
from llm_engineering.raw_data.documents.raw_document import RawDocument
from llm_engineering.raw_data.sources.base.extractor import BaseExtractor
from llm_engineering.raw_data.sources.base.health import SourceHealth
from llm_engineering.raw_data.sources.obsidian.markdown import clean_obsidian_markdown
from llm_engineering.raw_data.sources.obsidian.pdf_reader import read_pdf
from llm_engineering.raw_data.sources.obsidian.settings import ObsidianSettings
from llm_engineering.raw_data.sources.obsidian.vault import Note, ObsidianVault
from llm_engineering.registry.models.source import Source
from llm_engineering.registry.specs.obsidian import ObsidianSpec
from llm_engineering.utils.dates import to_utc_datetime
from llm_engineering.utils.globs import matches_any


class ObsidianExtractor(BaseExtractor[ObsidianSettings]):
    """Each registered vault: every note (minus excludes) as the owner's writing, plus selected PDFs
    (third-party by default). Topics from note tags + folder/file rules."""

    provider: ClassVar[str] = "obsidian"

    @staticmethod
    def vault(source: Source) -> ObsidianVault:
        spec: ObsidianSpec = source.typed_spec
        return ObsidianVault(
            spec.vault_path,
            include=spec.include,
            exclude=spec.exclude,
            skip_hidden=spec.skip_hidden,
            include_hidden=spec.include_hidden,
            source=source.id,
        )

    def extract_source(self, source: Source) -> Iterator[RawDocument]:
        spec: ObsidianSpec = source.typed_spec
        vault = self.vault(source)
        if not vault.exists():
            raise SourceUnavailableError(f"vault not found: {vault.root}", source=source.id)
        for note in vault.notes():
            if doc := self._note_document(source, spec, note):
                yield doc
        for rel in vault.pdf_paths(spec.pdf_include):
            if doc := self._pdf_document(source, spec, vault.root, rel):
                yield doc

    def _note_document(self, source: Source, spec: ObsidianSpec, note: Note) -> RawDocument | None:
        text = clean_obsidian_markdown(note.body)
        if len(text) < spec.min_chars:
            self.record_skipped(note.rel, f"shorter than {spec.min_chars} chars")
            return None
        return self.make_document(
            source=source,
            id=f"obsidian:{source.owner_id}:{note.rel}",
            kind="obsidian",
            origin="self",
            content=text,
            author=self.context.owner_name(source.owner_id),
            query=note.path.parts[0] if len(note.path.parts) > 1 else "/",
            topics=self._topics(spec, note.rel, note.tags),
            title=str(note.metadata.get("title") or note.path.stem),
            url=note.rel,
            created_at=to_utc_datetime(note.metadata.get("created") or note.metadata.get("date")),
            updated_at=note.modified_at,
            metadata={"tags": note.tags, "folder": note.path.parent.as_posix(), "file_type": "markdown"},
        )

    def _pdf_document(self, source: Source, spec: ObsidianSpec, root: Path, rel: Path) -> RawDocument | None:
        path = root / rel
        size_mb = path.stat().st_size / 1_048_576
        if size_mb > spec.pdf_max_mb:
            self.record_skipped(rel.as_posix(), f"PDF is {size_mb:.0f} MB > pdf_max_mb {spec.pdf_max_mb:.0f}")
            return None
        try:
            pdf = read_pdf(path, source=source.id)
        except ParseError as exc:
            self.record_failed(rel.as_posix(), str(exc))
            return None
        if len(pdf.text) < spec.min_chars:
            self.record_skipped(rel.as_posix(), f"shorter than {spec.min_chars} chars")
            return None
        owned = spec.pdf_origin == "self"
        return self.make_document(
            source=source,
            id=f"obsidian:{source.owner_id}:{rel.as_posix()}",
            kind="obsidian",
            origin=spec.pdf_origin,
            owned=owned,
            content=pdf.text,
            author=self.context.owner_name(source.owner_id) if owned else (pdf.author or "unknown"),
            query=rel.parts[0] if len(rel.parts) > 1 else "/",
            topics=self._topics(spec, rel.as_posix(), []),
            title=pdf.title or rel.stem,
            url=rel.as_posix(),
            metadata={"file_type": "pdf", "pages": pdf.pages, "folder": rel.parent.as_posix()},
        )

    def _topics(self, spec: ObsidianSpec, rel: str, tags: list[str]) -> set[str]:
        topics = self.context.matcher.from_vault_tags(tags)
        topics |= {r.topic for r in spec.topic_rules if matches_any(rel, [r.glob])}
        return topics

    def health_check(self, *, offline: bool = False) -> SourceHealth:
        details: dict[str, dict] = {}
        for source in self.sources:
            spec: ObsidianSpec = source.typed_spec
            vault = self.vault(source)
            if not vault.exists():
                return self.health(False, f"vault not found: {vault.root}")
            notes = [n.path for n in vault.notes()]
            pdfs = list(vault.pdf_paths(spec.pdf_include))
            by_folder = Counter(p.parts[0] if len(p.parts) > 1 else "/" for p in notes)
            details[source.id] = {"notes": len(notes), "pdfs": len(pdfs), "by_folder": dict(by_folder)}
        summary = ", ".join(f"{sid}: {d['notes']} notes, {d['pdfs']} PDFs" for sid, d in details.items())
        return self.health(True, summary or "no vaults registered", vaults=details)
