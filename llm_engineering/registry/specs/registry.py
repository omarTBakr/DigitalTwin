"""The `type` field of a declared source picks its spec model.
Adding a source type = a spec module + one entry here (+ its provider's extractor handling it)."""

from typing import Annotated

from pydantic import Field, TypeAdapter

from llm_engineering.registry.specs.article import ArticleSpec
from llm_engineering.registry.specs.github import GitHubSpec
from llm_engineering.registry.specs.linkedin import LinkedInExportSpec
from llm_engineering.registry.specs.medium_author import MediumAuthorSpec
from llm_engineering.registry.specs.medium_tag import MediumTagSpec
from llm_engineering.registry.specs.obsidian import ObsidianSpec

SourceSpec = Annotated[
    GitHubSpec | ObsidianSpec | LinkedInExportSpec | MediumTagSpec | MediumAuthorSpec | ArticleSpec,
    Field(discriminator="type"),
]
source_spec_adapter: TypeAdapter[SourceSpec] = TypeAdapter(SourceSpec)
