from langchain_community.document_loaders import ObsidianLoader

from llm_engineering.raw_data.sources.obsidian.markdown import strip_code_fences


class CodeAwareObsidianLoader(ObsidianLoader):
    """LangChain's ObsidianLoader (frontmatter, dataview fields, tags, file times), with one fix:
    tags inside fenced code blocks (C++ `#include`, shell comments) are not note tags.

    Overrides a private hook of ObsidianLoader; if a LangChain upgrade renames it, tags from code
    blocks simply reappear (nothing breaks) — re-check after upgrading langchain-community.
    """

    def _parse_document_tags(self, content: str) -> set[str]:
        return super()._parse_document_tags(strip_code_fences(content))
