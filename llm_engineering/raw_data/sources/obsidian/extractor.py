from collections import Counter
from collections.abc import Iterator
from typing import ClassVar

from llm_engineering.exceptions import ParseError, SourceUnavailableError
from llm_engineering.raw_data.documents.raw_document import RawDocument
from llm_engineering.raw_data.sources.base.extractor import BaseExtractor
from llm_engineering.raw_data.sources.base.health import SourceHealth
from llm_engineering.raw_data.sources.obsidian.markdown import (
    clean_obsidian_markdown,
    note_tags,
)
from llm_engineering.raw_data.sources.obsidian.settings import ObsidianSettings
from llm_engineering.raw_data.sources.obsidian.vault import Note, ObsidianVault
from llm_engineering.registry.models.source import Source
from llm_engineering.registry.specs.obsidian import ObsidianSpec
from llm_engineering.utils.dates import to_utc_datetime
from llm_engineering.utils.globs import matches_any


class ObsidianExtractor(BaseExtractor[ObsidianSettings]):
    """Every note of each registered vault (minus excludes); topics from tags + folder rules."""

    provider: ClassVar[str] = "obsidian"

    @staticmethod
    def vault(source: Source) -> ObsidianVault:
        spec: ObsidianSpec = source.typed_spec
        return ObsidianVault(
            spec.vault_path, include=spec.include, exclude=spec.exclude, skip_hidden=spec.skip_hidden, source=source.id
        )

    def extract_source(self, source: Source) -> Iterator[RawDocument]:
        vault = self.vault(source)
        if not vault.exists():
            raise SourceUnavailableError(f"vault not found: {vault.root}", source=source.id)
        for rel in vault.note_paths():
            try:
                note = vault.read(rel)
            except ParseError as exc:
                self.log.warning("%s", exc)
                self.record_failed(rel.as_posix(), str(exc))
                continue
            if doc := self._document(source, note):
                yield doc

    def _document(self, source: Source, note: Note) -> RawDocument | None:
        spec: ObsidianSpec = source.typed_spec
        text = clean_obsidian_markdown(note.body)
        if len(text) < spec.min_chars:
            self.record_skipped(note.rel, f"shorter than {spec.min_chars} chars")
            return None
        tags = note_tags(note.metadata, note.body)
        return self.make_document(
            source=source,
            id=f"obsidian:{source.owner_id}:{note.rel}",
            kind="obsidian",
            origin="self",
            content=text,
            author=self.context.owner_name(source.owner_id),
            query=note.path.parts[0] if len(note.path.parts) > 1 else "/",
            topics=self._topics(spec, note, tags),
            title=str(note.metadata.get("title") or note.path.stem),
            url=note.rel,
            created_at=to_utc_datetime(note.metadata.get("created") or note.metadata.get("date")),
            updated_at=note.modified_at,
            metadata={"tags": tags, "folder": note.path.parent.as_posix()},
        )

    def _topics(self, spec: ObsidianSpec, note: Note, tags: list[str]) -> set[str]:
        topics = self.context.matcher.from_vault_tags(tags)
        topics |= {r.topic for r in spec.topic_rules if matches_any(note.rel, [r.glob])}
        return topics

    def health_check(self, *, offline: bool = False) -> SourceHealth:
        details: dict[str, dict] = {}
        for source in self.sources:
            vault = self.vault(source)
            if not vault.exists():
                return self.health(False, f"vault not found: {vault.root}")
            paths = list(vault.note_paths())
            by_folder = Counter(p.parts[0] if len(p.parts) > 1 else "/" for p in paths)
            details[source.id] = {"notes": len(paths), "by_folder": dict(by_folder)}
        summary = ", ".join(f"{sid}: {d['notes']} notes" for sid, d in details.items())
        return self.health(True, summary or "no vaults registered", vaults=details)
