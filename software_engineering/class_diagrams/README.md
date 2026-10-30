# DigitalTwin: UML Class Diagrams

| | |
|---|---|
| Document status | v1.0, finalized from Draft v0.1 after principal review; for owner approval |
| Date | 2026-10-23 |
| Baseline | `main` at `4c40ca7` (ETL stage, P0). Code read only; nothing was run. |
| Inputs | [`requirements.md`](../requirements/requirements.md) v1.0, [`user_stories.md`](../user_stories/user_stories.md), the code under `llm_engineering/`, `steps/`, `pipelines/`, `tools/` |
| Review | [`class_diagram_review.md`](../reviews/class_diagram_review.md) lists every finding against the draft and the fix applied |
| Notation | Mermaid `classDiagram` (all 17 diagrams render with mermaid-cli 11.x) |

[← Hub](../README.md)

## How to read these diagrams

- **Implemented classes** have no `planned` stereotype. Their names, attributes, methods and types match the code at the baseline. Private helpers are shown with `-` and their real leading underscore. Python dunder methods are shown without underscores (`iadd` means `__iadd__`, `enter`/`exit` mean `__enter__`/`__exit__`), because Mermaid renders `__x__` as bold.
- **Keyword-only parameters.** A bare `*` inside a parameter list marks where keyword-only parameters start, as in Python (`GitHubClient(*, source: str, token: str | None)`).
- **Module constants** (for example `COLLECTION = "raw_documents"`) are shown in a `note for` the class that uses them, or in the `<<module>>` box of the module that defines them. They are never shown as class attributes unless the code declares them on the class.
- **Planned classes** carry the stereotype `<<planned Pn REQ-IDs>>`, for example `<<planned P1 REG-014>>`. `abstract` or `enum` is added where it applies (`<<planned abstract P2 FEA-004>>`). The `FR-` prefix is left out inside diagrams. NFR IDs keep their prefix. Section [14](#14-planned-classes-mapped-to-requirements) has the full mapping.
- **Planned stores** follow the existing three-part pattern (ABC, `Mongo*` implementation, `create_*()` factory). To keep the diagrams readable, only the ABC is drawn. Its box names the collection (`Mongo impl: collection runs`). Section [12.1](#121-key-patterns-in-the-implemented-code-keep-them-in-planned-work) states the convention.
- **Planned members of implemented classes** are not mixed into the class box, which shows only what exists. They are listed in a `note for <Class>` that starts with `planned`.
- Stereotypes used: `<<abstract>>` (an ABC), `<<pydantic>>` (Pydantic v2 `BaseModel`), `<<BaseSettings PREFIX_>>` (pydantic-settings, with its env prefix), `<<dataclass>>`, `<<enumeration>>` (a `Literal` type alias, shown as its values), `<<discriminated union>>`, `<<module>>` (module-level functions and constants, for example factories), `<<step>>` / `<<pipeline>>` (ZenML), `<<cli>>`, `<<external>>` (third-party class), `<<package>>` (overview only).
- `$` after a member means static, class-level or `ClassVar`. `*` after a method means abstract. `«property»`, `«cached»` and `«contextmanager»` mark `@property`, `@cached_property` and `@contextmanager`.
- Arrows: `<|--` inheritance (including subclassing an ABC), `*--` composition (the part has no life of its own), `o--` aggregation, `-->` association (a held reference), `..>` dependency (creates, uses, or reads).
- A class that belongs to another diagram appears again, with few or no members, where a relation needs it ("ref").

## Diagram index

| # | Diagram | Subsystem | Use cases | Sequence diagrams |
|---|---|---|---|---|
| 0 | [Overview](00_overview.md) | Packages and their dependencies (acyclic) |  | [SD-0](../sequence_diagrams/sd0_end_to_end.md), [SD-1](../sequence_diagrams/sd1_etl_pipeline_run.md) |
| 1 | [Settings and configuration](01_settings_and_configuration.md) | `settings/`, `crawl_config/`, `topics/` | [UC-01](../use_cases/01_configure_and_register_sources.md#uc-01-declare-topics-and-sources-in-yaml), [UC-02](../use_cases/01_configure_and_register_sources.md#uc-02-check-configuration-and-provider-health) | [SD-1](../sequence_diagrams/sd1_etl_pipeline_run.md) |
| 2a | [Registry core](02a_registry_core.md) | `registry/models`, `registry/store`, seeder, selector, keys | [UC-01](../use_cases/01_configure_and_register_sources.md#uc-01-declare-topics-and-sources-in-yaml), [UC-04](../use_cases/01_configure_and_register_sources.md#uc-04-register-a-source-through-the-ui-or-api), [UC-05](../use_cases/01_configure_and_register_sources.md#uc-05-manage-subscriptions-and-see-crawl-status), [UC-06](../use_cases/02_run_etl.md#uc-06-run-the-etl-pipeline), [UC-08](../use_cases/02_run_etl.md#uc-08-detect-changes-and-deletions-upstream) | [SD-1](../sequence_diagrams/sd1_etl_pipeline_run.md), [SD-3](../sequence_diagrams/sd3_trigger_incremental_etl.md), [SD-7](../sequence_diagrams/sd7_register_source_ui.md), [SD-8](../sequence_diagrams/sd8_account_deletion.md) |
| 2b | [Source specs](02b_source_specs.md) | `registry/specs` (the discriminated union) | [UC-01](../use_cases/01_configure_and_register_sources.md#uc-01-declare-topics-and-sources-in-yaml), [UC-04](../use_cases/01_configure_and_register_sources.md#uc-04-register-a-source-through-the-ui-or-api) |  |
| 3a | [Extraction framework](03a_extraction_framework.md) | `raw_data/sources/base`, `raw_data/sources/registry.py` | [UC-02](../use_cases/01_configure_and_register_sources.md#uc-02-check-configuration-and-provider-health), [UC-06](../use_cases/02_run_etl.md#uc-06-run-the-etl-pipeline), [UC-07](../use_cases/02_run_etl.md#uc-07-extract-content-from-a-provider), [UC-08](../use_cases/02_run_etl.md#uc-08-detect-changes-and-deletions-upstream) | [SD-1](../sequence_diagrams/sd1_etl_pipeline_run.md) |
| 3b | [Providers: Medium and GitHub](03b_providers_medium_and_github.md) | `raw_data/sources/{medium,github}`, `infrastructure/web` | [UC-07](../use_cases/02_run_etl.md#uc-07-extract-content-from-a-provider) | [SD-2](../sequence_diagrams/sd2_medium_extraction.md), [SD-3](../sequence_diagrams/sd3_trigger_incremental_etl.md) |
| 3c | [Providers: LinkedIn, Obsidian and Articles](03c_providers_linkedin_obsidian_and_articles.md) | `raw_data/sources/{linkedin,obsidian,articles}`, `raw_data/crawlers` | [UC-07](../use_cases/02_run_etl.md#uc-07-extract-content-from-a-provider), [UC-09](../use_cases/02_run_etl.md#uc-09-upload-a-linkedin-export-or-obsidian-vault) |  |
| 4 | [Raw storage and versioning](04_raw_storage_and_versioning.md) | `raw_data/{documents,store,snapshot}`, `infrastructure/{mongo,versioning}`, planned migrations | [UC-06](../use_cases/02_run_etl.md#uc-06-run-the-etl-pipeline), [UC-08](../use_cases/02_run_etl.md#uc-08-detect-changes-and-deletions-upstream), [UC-10](../use_cases/02_run_etl.md#uc-10-restore-a-raw-data-snapshot), [UC-23](../use_cases/06_admin_privacy_ops.md#uc-23-delete-my-account) | [SD-1](../sequence_diagrams/sd1_etl_pipeline_run.md), [SD-3](../sequence_diagrams/sd3_trigger_incremental_etl.md), [SD-4](../sequence_diagrams/sd4_feature_pipeline.md), [SD-8](../sequence_diagrams/sd8_account_deletion.md) |
| 5 | [Orchestration](05_orchestration.md) | `pipelines/`, `steps/etl/`, `tools/`, planned run records, change sets, locks, trigger kinds | [UC-02](../use_cases/01_configure_and_register_sources.md#uc-02-check-configuration-and-provider-health), [UC-06](../use_cases/02_run_etl.md#uc-06-run-the-etl-pipeline), [UC-08](../use_cases/02_run_etl.md#uc-08-detect-changes-and-deletions-upstream), [UC-10](../use_cases/02_run_etl.md#uc-10-restore-a-raw-data-snapshot), [UC-11](../use_cases/03_triggers_and_scheduling.md#uc-11-run-sources-on-a-schedule), [UC-24](../use_cases/06_admin_privacy_ops.md#uc-24-operate-and-monitor-the-system) | [SD-1](../sequence_diagrams/sd1_etl_pipeline_run.md), [SD-3](../sequence_diagrams/sd3_trigger_incremental_etl.md), [SD-4](../sequence_diagrams/sd4_feature_pipeline.md) |
| 6 | [Triggers and scheduling](06_triggers_and_scheduling.md) | planned | [UC-11](../use_cases/03_triggers_and_scheduling.md#uc-11-run-sources-on-a-schedule), [UC-12](../use_cases/03_triggers_and_scheduling.md#uc-12-trigger-ingestion-from-new-content), [UC-13](../use_cases/03_triggers_and_scheduling.md#uc-13-crawl-my-sources-on-demand) | [SD-0](../sequence_diagrams/sd0_end_to_end.md), [SD-3](../sequence_diagrams/sd3_trigger_incremental_etl.md), [SD-4](../sequence_diagrams/sd4_feature_pipeline.md), [SD-7](../sequence_diagrams/sd7_register_source_ui.md) |
| 7 | [Feature pipeline](07_feature_pipeline.md) | planned (clean, mask, chunk, embed, vector store, lineage) | [UC-14](../use_cases/04_rag_chat_and_features.md#uc-14-build-and-update-the-search-index), [UC-15](../use_cases/04_rag_chat_and_features.md#uc-15-exclude-or-forget-content), [UC-16](../use_cases/04_rag_chat_and_features.md#uc-16-chat-with-the-twin) | [SD-4](../sequence_diagrams/sd4_feature_pipeline.md), [SD-5](../sequence_diagrams/sd5_rag_chat.md), [SD-6](../sequence_diagrams/sd6_datasets_training_eval.md), [SD-8](../sequence_diagrams/sd8_account_deletion.md) |
| 8a | [Dataset generation](08a_dataset_generation.md) | planned | [UC-18](../use_cases/05_datasets_training_eval.md#uc-18-generate-training-datasets) | [SD-6](../sequence_diagrams/sd6_datasets_training_eval.md), [SD-8](../sequence_diagrams/sd8_account_deletion.md) |
| 8b | [Training, model registry and evaluation](08b_training_model_registry_and_evaluation.md) | planned | [UC-19](../use_cases/05_datasets_training_eval.md#uc-19-fine-tune-and-register-a-twin-model), [UC-20](../use_cases/05_datasets_training_eval.md#uc-20-evaluate-and-promote-a-model) | [SD-0](../sequence_diagrams/sd0_end_to_end.md), [SD-6](../sequence_diagrams/sd6_datasets_training_eval.md), [SD-8](../sequence_diagrams/sd8_account_deletion.md) |
| 9 | [LLM clients, inference and LLMOps](09_llm_clients_inference_and_llmops.md) | planned | [UC-16](../use_cases/04_rag_chat_and_features.md#uc-16-chat-with-the-twin), [UC-17](../use_cases/04_rag_chat_and_features.md#uc-17-give-feedback-on-an-answer), [UC-24](../use_cases/06_admin_privacy_ops.md#uc-24-operate-and-monitor-the-system) | [SD-3](../sequence_diagrams/sd3_trigger_incremental_etl.md), [SD-4](../sequence_diagrams/sd4_feature_pipeline.md), [SD-5](../sequence_diagrams/sd5_rag_chat.md), [SD-6](../sequence_diagrams/sd6_datasets_training_eval.md), [SD-8](../sequence_diagrams/sd8_account_deletion.md) |
| 10a | [UI, API and authentication](10a_ui_api_and_authentication.md) | planned | [UC-03](../use_cases/01_configure_and_register_sources.md#uc-03-sign-in-and-accept-the-terms), [UC-04](../use_cases/01_configure_and_register_sources.md#uc-04-register-a-source-through-the-ui-or-api), [UC-05](../use_cases/01_configure_and_register_sources.md#uc-05-manage-subscriptions-and-see-crawl-status), [UC-09](../use_cases/02_run_etl.md#uc-09-upload-a-linkedin-export-or-obsidian-vault), [UC-13](../use_cases/03_triggers_and_scheduling.md#uc-13-crawl-my-sources-on-demand), [UC-15](../use_cases/04_rag_chat_and_features.md#uc-15-exclude-or-forget-content), [UC-21](../use_cases/06_admin_privacy_ops.md#uc-21-administer-the-platform) | [SD-5](../sequence_diagrams/sd5_rag_chat.md), [SD-7](../sequence_diagrams/sd7_register_source_ui.md), [SD-8](../sequence_diagrams/sd8_account_deletion.md) |
| 10b | [Governance and privacy operations](10b_governance_and_privacy_operations.md) | planned (owner scope, purge contract, exclusions, deletion, export, taint) | [UC-15](../use_cases/04_rag_chat_and_features.md#uc-15-exclude-or-forget-content), [UC-22](../use_cases/06_admin_privacy_ops.md#uc-22-export-my-data), [UC-23](../use_cases/06_admin_privacy_ops.md#uc-23-delete-my-account) | [SD-6](../sequence_diagrams/sd6_datasets_training_eval.md), [SD-8](../sequence_diagrams/sd8_account_deletion.md) |
| 11 | [Exceptions](11_exceptions.md) | `llm_engineering/exceptions.py` plus planned subclasses |  |  |

## 12. Design notes

### 12.1 Key patterns in the implemented code (keep them in planned work)

1. **Template method plus strategy for extraction.** `BaseExtractor[S].extract()` fixes the control flow: session, loop over sources, error levels, abort, "all items failed means the source failed". Providers fill in `extract_source`, `health_check` and optionally `session`. The generic parameter `S` (bound to `BaseProviderSettings`) types each provider's tuning. Planned hooks (cursor, enumeration result, containing non-`SourceError` exceptions) go into the base class, so every provider gets them at once.
2. **Plugin registries keyed by name.** `PROVIDERS` (name to settings model and extractor class) and the `SourceSpec` discriminated union (`type` to spec model) are the only places that list providers and source types. Adding a source type means one spec module, one union entry and one extractor branch (NFR-MNT-001). Planned registries follow this: `feature_strategies.CLEANERS` and `CHUNKERS` (kind to strategy, module-level dicts like `PROVIDERS`, not registry classes), `vector_store_factory`, `PromptRegistry`, and the `SourceCursor` union (`kind` to cursor model).
3. **Repository plus factory per store.** `RawDataStore` / `RegistryStore` (ABCs) have `Mongo*` implementations and are chosen by `create_*_store(backend)` from `Settings`. The driver is imported only inside the factory branch. Implementations raise only `StorageError` subclasses. Every planned store keeps this three-part shape: `RunRecordStore` (runs and change sets), `LockManager`, `TriggerEventStore`, `CleanedDocumentStore`, `CostLedger`, `DeletionLogStore` (each `Mongo<Name>` plus `create_<name>()`), `VectorStore` (Qdrant), `DatasetStore` and `ModelRegistry` (private hub or DVC). The diagrams draw only the ABC and name the collection, because the `Mongo*` boxes would carry no information of their own.
4. **Context object and collecting parameter.** `CrawlContext` carries run-wide inputs (run id, topics, users, existing topic counts) into every extractor. `CrawlReport` collects per-item outcomes that become both the HTML artifact and the registry state. Planned inputs go into the context the same way (interactive flag, cursors, fingerprints, exclusions), and planned outputs into the report (enumerations). `RunRecord` and `ChangeSet` are built from the reports and `UpsertStats` of one run.
5. **Pydantic models as contracts.** `RawDocument` is the single output contract of extraction. Specs use `extra="forbid"` and validation context (topics). `Settings` groups one `BaseSettings` class per env prefix. Planned contracts (`CleanedDocument`, `Chunk`, `Sample`, `ModelVersion`, `EvalReport`, `Trace`, `Lineage`) are Pydantic models too, so they can be validated at every boundary and serialised into artifacts. Anything persisted polymorphically (cursors) is a discriminated union, never a bare ABC.
6. **Thin infrastructure adapters.** `Browser`, `GitHubClient`, `MediumFeedClient`, `DvcRepo`, `GitRepo` and `get_client()` wrap external tools and turn their errors into project exceptions. They are context managers where they hold resources. Planned adapters (`QdrantVectorStore`, `OpikTracer`, `HostedLLMClient`, `CloudGpuBackend`) must do the same. Cross-cutting HTTP behaviour (User-Agent, retries, `Retry-After`) is shared through `CrawlerSettings` and `RetryPolicy`, not copied per client.
7. **Steps are thin, logic is plain Python.** ZenML steps call plain functions or classes (`crawl_provider`, `RegistrySeeder`, `SourceSelector`, `RawDataSnapshotExporter`), so the logic runs and tests without ZenML. Planned pipelines (`feature_engineering`, `generate_datasets`, `training`) list their steps the same way and take an explicit upstream version as input (FR-ORC-005).
8. **Idempotency by stable ids.** Canonical source keys, stable document ids, `$setOnInsert` for state, `$addToSet` for lists. Planned downstream ids follow this: chunk `point_id` is a hash of document id, chunk index and cleaner version (FR-FEA-005), and dataset and model versions are immutable.
9. **One enforcement point per invariant (new).** Each cross-cutting rule has exactly one class that enforces it, and every caller goes through it: ownership at write time in `RegistryStore.upsert_source`; visibility at read time in `OwnerScope`; dataset admission in `TrainingDataSelector`; spend in `BudgetGuard`; "may this source run now" in `BackoffGate`; deletion through `Purgeable`.

### 12.2 Cross-cutting rules

- **`owner_id` isolation (G5, FR-REG-010).** Ownership is decided in exactly two places and enforced in exactly two places. Decided: `Source.from_spec` sets `Source.owner_id` from the declaring user for owned specs, and `BaseExtractor.make_document` copies it onto documents (or drops it with `owned=False`). Enforced at write: `RegistryStore.upsert_source` refuses to change an existing owner (`OwnershipConflictError`, FR-REG-012); without it, a second user who declares the owner's GitHub account becomes its owner. Enforced at read: `OwnerScope` (owner is the user, or null for shared external content). `VectorFilter` composes it, `CleanedDocumentStore.find` takes it, `TrainingDataSelector.select` takes it, and the training step's `check_dataset` calls `OwnerScope.assert_all` before any GPU time is spent (FR-FT-005). No other class filters by `owner_id` on behalf of a user. `owner_id` flows unchanged through `CleanedDocument`, `Chunk` payloads, `Sample` and `ModelVersion`. `RawDataStore.find(owner_id=...)` keeps its current meaning ("this user's own writing"), used by export and dataset building, not by retrieval.
- **Self/external origin (G2).** `origin` is decided once, at extraction (`make_document`, `pdf_origin`, `ArticleSpec.origin`). Invariant DQ-4: `owner_id` is set if and only if `origin=self`. Today `ArticleSpec(origin=self)` breaks it (FR-ART-005). Downstream only reads `origin`: style samples need `self` plus a positive `style_eligible`, external samples need the source's licence, both checked in `TrainingDataSelector`. Retrieval may return both.
- **Exclusions and forgetting.** An `Exclusion` (document, source or glob; scopes crawl, retrieval, training) is stored in the registry. It is enforced at crawl time through `CrawlContext.exclusions`, at retrieval time by deleting the vectors (`ExclusionService` or `tools.forget` through `Purgeable`), and at dataset time by `TrainingDataSelector` (FR-UI-006, FR-PRV-006).
- **Canonical keys and dedup.** All source ids come from `registry/keys.py`. A key change is a data migration (it would duplicate sources), so any change needs `SchemaMigrator` and tests (RISK-05).
- **Error levels.** Item, source, provider, run (FR-ETL-002). Planned code raises project exceptions only (section [11](11_exceptions.md)). New infrastructure errors map into `StorageError` or `SourceError`, never driver types.
- **Lineage.** `run_id` (ZenML run name) is in `Provenance`, `SourceState` and, later, `RunRecord`. `data_md5` plus the git commit identify a raw snapshot. Each downstream artifact carries a `Lineage` (raw `data_md5`, snapshot commit, code commit, upstream version ids): cleaned documents, the vector collection, dataset versions, model versions and eval reports (FR-VER-004). Dataset versions also list their source document ids, which is how deletions reach models (`TaintTracker`, FR-PRV-005).
- **Change-set contract.** The only ETL to feature-pipeline interface is `ChangeSet` (inserted, changed, tombstoned ids) (FR-ORC-008). Tombstones are inferred only from a complete enumeration (`EnumerationResult.complete`, then `missing()`), never from feeds or truncated trees (FR-ETL-010, FR-GH-004).
- **Change detection.** Cursors hold only source-level watermarks (ETag, `Last-Modified`, last feed GUID, `pushed_at` per repo, vault mtime). Per-item fingerprints (content hash, GitHub blob SHA in `metadata.sha`) are read from the raw store into `CrawlContext.fingerprints` once per run, the way `existing_topics` is today, so the `sources` collection does not grow with the number of files (FR-REG-011, FR-REG-014).
- **Unattended by default.** `RunOptions.interactive=False` for scheduled and triggered runs. No browser in that mode (FR-MED-008, NFR-CMP-002).
- **Money.** Every paid call estimates its cost first (`Embedder`, `LLMClient`, `SampleGenerator`, `ComputeBackend`), calls `BudgetGuard.ensure(stage, estimate, user_id)`, and records the actual cost with `BudgetGuard.charge`. The ledger entry names the user, so per-user daily caps work (FR-OPS-008, FR-INF-008, FR-UI-012). Per-run caps (`EmbeddingSettings.max_usd`, `TrainingConfig.max_usd`) are inputs to the same guard, not separate checks.
- **One reader per input.** The environment is read only by `get_settings()`, YAML only by `YamlLoader`. Planned settings groups (vector store, embeddings, LLM, budgets, API, scheduler, tracing, crawler identity) are new `BaseSettings` classes on `Settings`.
- **Acyclic packages.** Section [0](00_overview.md) is acyclic. Two rules keep it so: `governance` and `run_tracking` import no other planned package, and adapters take plain values across package boundaries (the tracer takes a name and a user id, not a `ChatRequest`).

### 12.3 Code and requirements mismatches noticed while drawing

1. **The brief says `RawDocument` has a `kind` field. The code calls it `source: SourceKind`.** `make_document(kind=...)` maps `kind` to `source`. Requirements FR-ETL-004 and section 5.1 already use `source`. The planned `CleanedDocument` and `Chunk` use `kind`, which is clearer. Consider renaming `RawDocument.source` to `kind` with a schema migration (FR-STO-007).
2. **Two classes are named `GitHubSettings`.** `settings/app_settings.py` (token) and `raw_data/sources/github/settings.py` (`request_delay_s`). They are in different modules and are not imported together today, but the clash makes diagrams and imports confusing. Suggest renaming the first to `GitHubApiSettings`.
3. **`MediumSettings.skip_member_only` is never read** (already FR-CFG-005).
4. **The `crawl_medium` step docstring says "(Selenium)".** Article text comes from RSS, and Selenium is used only for tag discovery.
5. **Extractors set attributes outside `__init__`.** `GitHubExtractor.client` and `MediumExtractor.counts`, `known`, `feeds`, `listing` and `listing_blocked` exist only inside `session()`. The diagrams show them as attributes. Declaring them in `__init__` (as `None`) would help type checking (NFR-MNT-003).
6. **`create_registry_store` reads `RAW_STORE_BACKEND`.** The registry and the raw store cannot use different backends. That is fine today but undocumented in `Settings`.
7. **`ArticlesExtractor.crawler` is a property that builds a new `CustomArticleCrawler` on each access.** It runs once per source and once in the health check. This is harmless, but a session-scoped crawler would match the other providers.
8. **The requirements' gap statements match the code.** These were confirmed while drawing: `_find_in_feed` catches `RateLimitError` (FR-MED-005), 5xx exhaustion raises `RateLimitError`, `upsert_source` `$set`s `owner_id` (it is in `DECLARATION_FIELDS`, FR-REG-012), `record_state` overwrites the whole state (FR-REG-014), `ObsidianVault.notes()` fails the whole vault on one bad file (FR-OBS-006), and the article UA is a copied Chrome string (FR-ART-002). No requirement claims an implemented behaviour that the code lacks.
9. **The registry depends on the raw-data package for one type alias.** `registry/specs/{article,obsidian}.py` import `Origin` from `raw_data/documents/types.py`. It is not a cycle today, but it points from the more stable package to the less stable one. Moving `Origin` and `SourceKind` to a shared module (for example `llm_engineering/domain/types.py`) removes the edge.
10. **Two crawlers already identify themselves, one does not.** `MediumFeedClient` and `GitHubClient` send `DigitalTwinCrawler/0.1` (without a contact URL); `CustomArticleCrawler` sends a copied Chrome string. `CrawlerSettings` gives all three one identifying UA (FR-ART-002, NFR-CMP-003).
11. **`.env.example` claims the GitHub token is needed for private repos** while the code calls `/users/{u}/repos` (public only). Already in FR-GH-007; the comment should be fixed now.

## 13. Class counts

Counted with a script over the Mermaid blocks (each class box once per diagram, refs excluded). The draft column is the same count over [`class_diagram_draft.md`](../reviews/class_diagram_draft.md).

| Diagram | Implemented (not counting refs) | Planned, draft | Planned, final |
|---|---|---|---|
| 1 Settings and configuration | 12 | 8 | 8 |
| 2a Registry core | 13 | 8 | 6 |
| 2b Source specs | 12 | 0 | 0 |
| 3a Extraction framework | 20 | 5 | 3 |
| 3b Medium and GitHub | 15 | 3 | 3 |
| 3c LinkedIn, Obsidian, Articles | 18 | 4 | 1 |
| 4 Raw storage and versioning | 13 | 7 | 7 |
| 5 Orchestration | 15 | 14 | 11 |
| 6 Triggers | 0 | 18 | 14 |
| 7 Feature pipeline | 0 | 30 | 29 |
| 8a Datasets | 0 | 27 | 21 |
| 8b Training and evaluation | 0 | 23 | 24 |
| 9 LLM clients, inference and LLMOps | 0 | 33 | 29 |
| 10a UI and API | 0 | 25 | 18 |
| 10b Governance and privacy | 0 | 17 | 10 |
| 11 Exceptions | 19 | 13 | 14 |
| **Unique across all diagrams** | **124** (draft: 121) | **235** | **198** |

Some implemented classes appear in full in two diagrams (the five extractors in 3a as stubs and in 3b/3c; `GitHubSettings` in 1 and again in 3b as "GitHubSettings (app_settings)"), so the column sum is larger than the unique total. The implemented count rose by 3 because three invented helper modules of the draft (`medium_helpers`, `github_support`, `obsidian_helpers`) were replaced by the six real modules they stood for. These counts include `<<module>>`, `<<step>>`, `<<pipeline>>`, `<<cli>>` and `<<enumeration>>` boxes. The overview's package boxes are not counted.

The planned count fell by 37 (16%): 53 draft names are gone and 16 names are new. Of the 53, 7 trivial `Mongo*` boxes became a stated convention, 6 empty router classes became members of `ApiApp`, 6 `Purger` subclasses became one `Purgeable` interface implemented by the stores, and the rest were folded into the class that owns the behaviour (for example `TombstonePolicy` into `EnumerationResult.missing()`, `TriggerRetryPolicy` into `BackoffGate`, `CollectionAliasManager` into `VectorStore`, `CostEstimator` into `LLMClient.estimate_cost_usd`). Of the 16 new names, 10 are merges or renames of draft classes (`HttpCursor`, `RegexMasker`, `Masker`, `NerRedactor`, `feature_strategies`, `QueryExpander`, `CrawlerSettings`, `VectorStoreSettings`, `EvalSet`, `tools_forget`) and 6 fill a gap the draft left open (`Purgeable`, `OwnerScope`, `TrainingDataSelector`, `Lineage`, `Sample`, `OwnerIsolationError`). The review lists each change.

## 14. Planned classes mapped to requirements

Every planned class has at least one requirement, and every Must requirement of P1 to P4 that implies structure has a class, attribute or method home (the review's coverage table checks them one by one).

| Planned class | Diagram | Phase | Requirement IDs |
|---|---|---|---|
| VectorStoreSettings | 1 | P2 | FR-FEA-004, NFR-SCL-002 |
| EmbeddingSettings | 1 | P2 | FR-FEA-003, FR-FEA-009 |
| LLMSettings | 1 | P2 | FR-INF-003, FR-DS-007, OQ-05 |
| BudgetSettings | 1 | P2 | NFR-COST-001, FR-OPS-008 |
| ApiSettings | 1 | P2 | FR-INF-005, FR-INF-008 |
| SchedulerSettings | 1 | P1 | FR-TRG-002, FR-TRG-003, FR-TRG-004, FR-TRG-006, FR-TRG-008 |
| TracingSettings | 1 | P2 | FR-OPS-001, NFR-PRIV-004 |
| CrawlerSettings | 1 | P1 | FR-ART-002, NFR-CMP-003 |
| SourceCursor (+ HttpCursor, GitHubCursor, VaultCursor) | 2a, 3b, 3c | P1 | FR-REG-014, FR-REG-011, FR-GH-005, FR-TRG-003 |
| DeclaredVia | 2a | P4 | FR-CFG-008 |
| DeclarationMerger | 2a | P1 | FR-REG-013, NFR-SCL-001 |
| RegistryReconciler | 2a | P1 | FR-REG-008, FR-REG-009, FR-PRV-003 |
| OrphanSourcePolicy | 2a | P1 | FR-PRV-003, FR-REG-008 |
| SelectionResult | 2a | P1 | FR-REG-007, FR-UI-010 |
| EnumerationResult | 3a | P1 | FR-ETL-010, FR-GH-004, FR-OBS-004 |
| RetryPolicy | 3a | P1 | FR-MED-005, NFR-REL-005, NFR-CMP-003 |
| RobotsPolicy | 3a | P1 | FR-ART-003, NFR-CMP-001 |
| VendoredCodeClassifier | 3b | P2 | FR-GH-006 |
| SchemaMigration, SchemaMigrator | 4 | P1 | FR-STO-007 |
| SnapshotPublisher, SnapshotRef | 4 | P1 | FR-VER-006, FR-ORC-007 |
| SnapshotRestorer | 4 | P1 | FR-VER-007, FR-OPS-009 |
| SnapshotLayout | 4 | P4 | FR-VER-008, FR-PRV-002 |
| TopicMigrator | 4 | P2 | FR-CFG-007 |
| TriggerKind | 5 | P1 | FR-TRG-008, FR-ORC-007 |
| RunOptions | 5 | P1 | FR-MED-008, FR-TRG-002 |
| RunRecord, CrawlSummary | 5 | P1 | FR-ORC-007, FR-ORC-003, NFR-COST-002 |
| RunRecordStore | 5 | P1 (change sets P2) | FR-ORC-007, FR-ORC-008 |
| ChangeSet | 5 | P2 | FR-ORC-008, FR-STO-005, FR-TRG-005 |
| LockManager, Lease | 5 | P1 | FR-ORC-006 |
| record_run (step) | 5 | P1 | FR-ORC-007, FR-OPS-006 |
| publish_change_set (step) | 5 | P2 | FR-ORC-008 |
| tools_restore_snapshot (cli) | 5 | P1 | FR-VER-007 |
| TriggerEvent, TriggerEventStore | 6 | P1 | FR-TRG-008, FR-TRG-007 |
| TriggerSource, GitHubPushPoller, MediumFeedPoller, VaultWatcher | 6 | P1 | FR-TRG-003 |
| Scheduler, ScheduleEntry | 6 | P1 | FR-TRG-002 |
| Coalescer, TriggerBatch | 6 | P1 | FR-TRG-004 |
| BackoffGate | 6 | P1 | FR-TRG-006, FR-TRG-008, FR-REG-014 |
| TriggerDispatcher | 6 | P1 | FR-TRG-002, FR-TRG-003, FR-ORC-006 |
| FeatureRunTrigger | 6 | P2 | FR-TRG-005 |
| GitHubWebhookVerifier | 6 | P4 | FR-TRG-007 |
| feature_engineering (pipeline) | 7 | P2 | FR-FEA-001, FR-ORC-005, FR-VER-004 |
| Lineage | 7 | P2 | FR-VER-004, FR-ORC-005, FR-FT-004 |
| CleanedDocument | 7 | P2 | FR-FEA-001, FR-FEA-006, FR-DS-008 |
| Cleaner, MarkdownCleaner, CodeCleaner, PostCleaner | 7 | P2 | FR-FEA-001 |
| feature_strategies (module) | 7 | P2 | FR-FEA-001, FR-FEA-002 |
| QualityGate | 7 | P2 | FR-FEA-007 |
| Masker, RegexMasker | 7 | P2 | FR-FEA-008 |
| NerRedactor | 7 | P3 | FR-PRV-004 |
| DuplicateDetector, DuplicateGroup | 7 | P2 | FR-ETL-011, FR-DS-004 |
| CleanedDocumentStore | 7 | P2 | FR-FEA-006, OQ-04 |
| Chunk, Chunker, HeadingChunker, CodeChunker, WholeDocumentChunker | 7 | P2 | FR-FEA-002, FR-FEA-005 |
| EmbeddingModelInfo, Embedder, LocalEmbedder, HostedEmbedder | 7 | P2 | FR-FEA-003, FR-FEA-009 |
| VectorFilter, ScoredChunk | 7 | P2 | FR-FEA-004, FR-REG-010, FR-INF-002 |
| VectorStore, QdrantVectorStore, vector_store_factory | 7 | P2 | FR-FEA-004, FR-FEA-005, FR-FEA-010, NFR-SCL-002, NFR-PERF-005 |
| generate_datasets (pipeline) | 8a | P3 | FR-DS-001, FR-ORC-005 |
| TrainingDataSelector | 8a | P3 | FR-DS-001, FR-DS-006, FR-DS-008, FR-REG-010, FR-UI-006, NFR-CMP-004 |
| StyleEligibilityPolicy | 8a | P3 | FR-DS-008 |
| Sample, InstructionSample | 8a | P3 | FR-DS-001 |
| PreferenceSample | 8a | P3 | FR-DS-002 |
| SampleGenerator, InstructionGenerator, PreferenceGenerator | 8a | P3 | FR-DS-001, FR-DS-002, FR-DS-007 |
| SampleFilter, DedupFilter, LengthFilter, JudgeFilter, FilterReport | 8a | P3 | FR-DS-003 |
| DocumentSplitter | 8a | P3 | FR-DS-004 |
| DatasetVersion | 8a | P3 | FR-VER-005, FR-VER-004, FR-PRV-005 |
| DatasetCard | 8a | P3 | FR-DS-005, NFR-CMP-005 |
| DatasetQualityGate | 8a | P3 | FR-DS-010 |
| DatasetStore, PrivateHubDatasetStore, DvcDatasetStore | 8a | P3 | FR-VER-005, FR-PRV-005, NFR-PRIV-001 |
| training (pipeline) | 8b | P3 | FR-FT-001, FR-ORC-005, FR-FT-005 |
| TrainingConfig | 8b | P3 | FR-FT-003 |
| Trainer, SftTrainer, DpoTrainer | 8b | P3 | FR-FT-001, FR-FT-002 |
| ComputeBackend, LocalGpuBackend, CloudGpuBackend, JobHandle | 8b | P3 | FR-FT-006 |
| ModelVersion, ModelTag | 8b | P3 | FR-FT-004, FR-PRV-005 |
| ModelRegistry, PrivateHubModelRegistry | 8b | P3 | FR-FT-004, FR-PRV-005, NFR-PRIV-001 |
| EvalSet, EvalItem | 8b | P2 | FR-DS-009, FR-EVAL-003, FR-EVAL-005 |
| Evaluator, MetricScore, EvalReport | 8b | P2 | FR-EVAL-001, FR-EVAL-003, FR-VER-004 |
| StyleSimilarityEvaluator, AnswerQualityEvaluator | 8b | P3 | FR-EVAL-001 |
| BenchmarkRegressionEvaluator | 8b | P3 | FR-EVAL-002 |
| RagEvaluator | 8b | P2 | FR-EVAL-003 |
| SafetyEvaluator | 8b | P3 | FR-EVAL-005, NFR-SEC-006 |
| PromotionGate | 8b | P3 | FR-EVAL-004, FR-OPS-004 |
| TwinService | 9 | P2 | FR-INF-001, FR-INF-004, FR-INF-006, FR-INF-007 |
| ChatRequest, ChatTurn, ChatResponse, SourceCitation | 9 | P2 | FR-INF-001, FR-INF-006, FR-INF-007 |
| Retriever | 9 | P2 | FR-INF-002, FR-INF-007, FR-REG-010 |
| QueryExpander, SelfQueryExtractor, CrossEncoderReranker | 9 | P2 | FR-INF-002 |
| ModelResolver | 9 | P3 | FR-INF-003, FR-FT-004 |
| PromptTemplate, PromptRegistry | 9 | P2 | FR-OPS-002 |
| LLMClient, BaseModelClient, Completion | 9 | P2 | FR-INF-003, FR-OPS-001, FR-DS-007 |
| AdapterModelClient | 9 | P3 | FR-INF-003, FR-FT-004 |
| HostedLLMClient | 9 | P3 | FR-DS-001, FR-EVAL-001, OQ-05 |
| Tracer, OpikTracer, Trace | 9 | P2 | FR-OPS-001, NFR-PRIV-004 |
| Feedback | 9 | P4 | FR-OPS-007 |
| CostEntry, CostLedger, BudgetGuard | 9 | P2 | FR-OPS-008, NFR-COST-001, NFR-COST-002, FR-INF-008, FR-UI-012 |
| RateLimiter | 9 | P2 | FR-INF-008, FR-UI-004 |
| Alerter, AlertRule | 9 | P1 | FR-OPS-005, FR-OPS-006 |
| MetricsExporter | 9 | P1 | NFR-OBSV-004 |
| BackupJob | 9 | P1 | FR-OPS-009, NFR-REL-007 |
| ApiApp (with its routers) | 10a | P2 (routers P2/P4) | FR-UI-008, FR-INF-001, FR-UI-001..007, FR-LI-004, FR-TRG-007 |
| AuthService, BearerTokenAuth, Principal, Role | 10a | P2 | FR-INF-005, FR-UI-009 |
| SessionAuthService, Invite | 10a | P4 | FR-UI-009, NFR-SEC-003, OQ-14 |
| Consent | 10a | P4 | FR-UI-010, NFR-CMP-006 |
| Credential, CredentialVault | 10a | P4 | FR-UI-005, NFR-SEC-004 |
| GitHubOAuthVerifier | 10a | P4 | FR-UI-011, FR-REG-012 |
| SourceRegistrationService, SubscriptionView | 10a | P4 | FR-UI-001, FR-UI-002, FR-UI-003, FR-CFG-008 |
| OnDemandCrawlService | 10a | P4 | FR-UI-004 |
| QuotaPolicy | 10a | P4 | FR-UI-012, FR-INF-008 |
| ExclusionService | 10a | P4 | FR-UI-006 |
| UploadService, SafeZipExtractor | 10a | P4 | FR-LI-004, FR-OBS-005, FR-UI-005 |
| OwnerScope | 10b | P2 | FR-REG-010, FR-FT-005, FR-INF-002 |
| PurgeScope, Purgeable | 10b | P1 | FR-STO-006, FR-PRV-002, FR-PRV-006, FR-FEA-005, NFR-PRIV-004 |
| Exclusion | 10b | P2 | FR-UI-006, FR-PRV-006, FR-OBS-004 |
| AccountDeletionService | 10b | P4 | FR-PRV-002, FR-VER-008 |
| DataExportService | 10b | P4 | FR-PRV-001 |
| tools_forget (cli) | 10b | P2 | FR-PRV-006 |
| DeletionLog, DeletionLogStore | 10b | P1 | FR-PRV-002, FR-PRV-006 |
| TaintTracker | 10b | P4 | FR-PRV-005 |
| OwnershipConflictError | 11 | P1 | FR-REG-012 |
| LockHeldError | 11 | P1 | FR-ORC-006 |
| VectorStoreError | 11 | P2 | FR-FEA-004 |
| DatasetQualityError | 11 | P3 | FR-DS-010 |
| PromotionRejectedError | 11 | P3 | FR-EVAL-004 |
| BudgetExceededError | 11 | P2 | FR-OPS-008, NFR-COST-001, FR-INF-008 |
| AccessError, UnauthenticatedError, PermissionDeniedError, QuotaExceededError | 11 | P2/P4 | FR-INF-005, FR-UI-007, FR-UI-009, FR-UI-012, FR-INF-008 |
| OwnerIsolationError | 11 | P2 | FR-REG-010, FR-FT-005 |
| WebhookSignatureError | 11 | P4 | FR-TRG-007 |
| InferenceError, ModelUnavailableError | 11 | P2/P3 | FR-INF-003 |

Planned members of implemented classes (shown in notes, not as classes): `SourceState` cursor and success fields (FR-REG-014), `Source.declared_via` / `schema_version` / `license_allows_training` (FR-CFG-008, FR-STO-007, FR-DS-006), `Subscription` per-subscriber fields (FR-REG-013), `User` email, role, disabled, consent and quotas (FR-UI-009, FR-UI-010, FR-UI-012), `SeedStats` removal counts (FR-REG-009), `SourceSelector` consent filter (FR-UI-010), `RegistryStore` owner-preserving upsert, unsubscribe, delete, purge, exclusions and consent (FR-REG-012, FR-REG-008/009, FR-PRV-002, FR-UI-006, FR-UI-010), `RawDocument` lifecycle fields and `topics_by_source` (FR-ETL-010, FR-STO-005/006/007, FR-ETL-013), `RawDataStore` tombstone, purge, fingerprints and topic replacement (FR-STO-006, FR-REG-011, FR-ETL-013), `UpsertStats.changed` and id lists (FR-STO-005), spec additions (FR-MED-007, FR-ART-005, FR-GH-006/007, FR-OBS-004, FR-DS-006), `BaseExtractor` hooks and fault containment (FR-ETL-012, FR-REG-011, FR-ETL-010), `CrawlContext` interactive flag, cursors, fingerprints and exclusions (FR-MED-008, FR-REG-014, FR-REG-011, FR-UI-006), `CrawlReport` enumerations (FR-ETL-010, FR-GH-004), `MediumFeedClient` back-off fixes (FR-MED-005), `GitHubClient` truncation and SHA (FR-GH-004/005/007), `ObsidianVault` per-file loading and privacy flag (FR-OBS-006, FR-OBS-004), `CustomArticleCrawler` UA and byline (FR-ART-002, FR-ART-004), `Topic.renamed_from` (FR-CFG-007).
