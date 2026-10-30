# SD-1. ETL pipeline run (implemented)

[← Sequence diagrams](README.md) · [Hub](../README.md) · Previous: [SD-0](sd0_end_to_end.md) · Next: [SD-2](sd2_medium_extraction.md)

| | |
|---|---|
| Status | Implemented (P0) |
| Requirements | [ETL](../requirements/requirements.md#23-extraction-framework-etl) 001, 002, 003, 004, 005, 006, 007, 008, 009 · [ORC](../requirements/requirements.md#26-orchestration-and-cli-orc) 001, 002, 003, 004 · [REG](../requirements/requirements.md#22-source-registry-and-multi-user-reg) 005, 006, 007 · [VER](../requirements/requirements.md#27-data-versioning-ver) 001, 002, 003 |
| User stories | US-007, US-008, US-009, US-015, US-016, US-017, US-018, US-019, US-039, US-040, US-043 ([backlog](../user_stories/user_stories.md)) |
| Use cases | [UC-01](../use_cases/01_configure_and_register_sources.md#uc-01-declare-topics-and-sources-in-yaml), [UC-06](../use_cases/02_run_etl.md#uc-06-run-the-etl-pipeline) |
| Class diagrams | [0](../class_diagrams/00_overview.md), [1](../class_diagrams/01_settings_and_configuration.md), [2a](../class_diagrams/02a_registry_core.md), [2b](../class_diagrams/02b_source_specs.md), [3a](../class_diagrams/03a_extraction_framework.md), [4](../class_diagrams/04_raw_storage_and_versioning.md), [5](../class_diagrams/05_orchestration.md) |
| draw.io | copy the ```mermaid block below → Arrange › Insert › Mermaid |


`uv run python -m tools.run --etl [--user U] [--source ID ...]` builds and runs the ZenML pipeline. The five crawl steps have the same body (`run_crawl_step` → `crawl_provider`); the loop shows one provider. On the local orchestrator they run one after another.

```mermaid
sequenceDiagram
  autonumber
  actor Owner
  participant CLI as tools.run
  participant ZenML as digital_data_etl (ZenML)
  participant Sync as sync_registry
  participant Loader as YamlLoader
  participant Seeder as RegistrySeeder
  participant RegStore as MongoRegistryStore
  participant Select as select_sources / SourceSelector
  participant Step as crawl_<provider> / run_crawl_step
  participant Crawl as crawl_provider
  participant Ext as BaseExtractor subclass
  participant Store as MongoRawDataStore
  participant Ver as version_raw_data
  participant Exp as RawDataSnapshotExporter
  participant Dvc as DvcRepo
  participant Git as GitRepo
  participant Sum as summarize_crawl

  Owner->>CLI: --etl --user omar
  CLI->>ZenML: digital_data_etl(user_id, source_ids) with run name
  ZenML->>Sync: sync_registry()
  Sync->>Loader: users (profile.yaml + sources/*.yaml, validated with topics)
  Loader-->>Sync: UserDeclaration per user
  Sync->>Seeder: seed(declarations)
  Seeder->>RegStore: upsert_user, bulk source_upsert_op ($set declaration, $setOnInsert state), subscribe
  Note over Seeder,RegStore: planned REG-012/013: refuse owner change, merge shared declarations
  Seeder-->>Sync: SeedStats (registry_sync artifact)
  ZenML->>Select: select_sources(registry_sync, user_id, source_ids)
  Select->>RegStore: users, subscriptions, sources
  alt unknown user or source id
    Select-->>ZenML: UnknownUserError / UnknownSourceError (run stops before any fetch)
  else
    Select-->>ZenML: selection {provider: [source ids]}
  end

  loop each provider: medium, github, linkedin, obsidian, articles
    ZenML->>Step: crawl_<provider>(selection)
    Step->>Crawl: crawl_provider(provider, ids, current_run_id())
    alt no source ids for this provider
      Crawl-->>Step: status skipped
    else
      Crawl->>RegStore: sources(ids), users()
      Crawl->>Store: setup(), topics_by_id(provider)
      Crawl->>Ext: create_extractor(provider, settings, sources, CrawlContext)
      Crawl->>Ext: extract()
      activate Ext
      Note over Ext: session() opens clients or browser once per provider
      loop each source
        Ext->>Ext: extract_source(source) yields RawDocument via make_document
        alt item-level problem
          Ext->>Ext: report.failed / skipped (reason)
        else SourceError for this source
          Ext->>Ext: report.source_failed, continue with the next source
        else AccessBlocked / Authentication / RateLimit
          Ext->>Ext: _abort: remaining sources marked not crawled
        end
        Ext-->>Crawl: RawDocument (streamed)
        Crawl->>Crawl: report.ok, add to batch
        opt batch reaches 50
          Crawl->>Store: upsert_many(batch) ($set fields, $addToSet topics + source_ids, $push provenance)
        end
      end
      Ext->>Ext: _fail_sources_without_successes()
      deactivate Ext
      Note over Crawl,Ext: planned ETL-012: a non-SourceError is contained per source too
      Crawl->>Store: finally: flush remaining batch
      Crawl->>RegStore: record_states(report, run_id)
      Crawl->>Store: count, counts_by_topic
      Crawl-->>Step: (summary, CrawlReport)
    end
    Step->>ZenML: log_metadata(summary)
    Step-->>ZenML: summary + HTMLString(render_crawl_report)
  end

  ZenML->>Ver: version_raw_data(crawl_summaries)
  opt DVC_ENABLED
    Ver->>Exp: export(providers)
    Exp->>Store: find(provider) per provider
    Exp->>RegStore: users, sources, subscriptions
    Exp-->>Ver: record counts (data/raw/*.jsonl, atomic writes)
    Ver->>Dvc: add(data/raw), tracked_hash
    opt DVC_AUTO_COMMIT
      Ver->>Git: commit_paths(pointer, .gitignore, DVC setup files)
    end
    opt DVC_AUTO_PUSH
      Ver->>Dvc: push(remote)
    end
    Note over Ver,Git: planned VER-006: push before commit, commit off the working branch
  end
  Ver-->>ZenML: versioning_summary (failure reported, never raised)
  ZenML->>Sum: summarize_crawl(summaries, versioning)
  alt any provider failed or versioning failed
    Sum-->>ZenML: PipelineError (data already stored is kept)
  else
    Sum-->>ZenML: ok / partial
  end
  ZenML-->>CLI: run finished
  CLI-->>Owner: exit code, dashboard at 127.0.0.1:8237
```
