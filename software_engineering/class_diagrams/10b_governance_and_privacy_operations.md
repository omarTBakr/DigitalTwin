# 10b. Governance and privacy operations (planned)

[← Class diagrams](README.md) · [Hub](../README.md) · Previous: [10a. UI, API and authentication (planned)](10a_ui_api_and_authentication.md) · Next: [11. Exceptions](11_exceptions.md)

| | |
|---|---|
| Status | Planned |
| Subsystem | planned (owner scope, purge contract, exclusions, deletion, export, taint) |
| Requirements | [FEA](../requirements/requirements.md#210-feature-pipeline-fea) 005 · [FT](../requirements/requirements.md#212-fine-tuning-ft) 005 · [INF](../requirements/requirements.md#214-rag-inference-service-inf) 002 · [OBS](../requirements/requirements.md#obsidian-obs) 004 · [PRV](../requirements/requirements.md#216-privacy-and-data-subject-operations-prv) 001, 002, 005, 006 · [REG](../requirements/requirements.md#22-source-registry-and-multi-user-reg) 010 · [STO](../requirements/requirements.md#25-raw-storage-sto) 006 · [UI](../requirements/requirements.md#29-source-registration-ui-and-api-ui) 006 · [VER](../requirements/requirements.md#27-data-versioning-ver) 008 · [NFR-PRIV](../requirements/requirements.md#35-privacy-priv) 004 |
| Use cases | [UC-15](../use_cases/04_rag_chat_and_features.md#uc-15-exclude-or-forget-content), [UC-22](../use_cases/06_admin_privacy_ops.md#uc-22-export-my-data), [UC-23](../use_cases/06_admin_privacy_ops.md#uc-23-delete-my-account) |
| Sequence diagrams | [SD-6](../sequence_diagrams/sd6_datasets_training_eval.md), [SD-8](../sequence_diagrams/sd8_account_deletion.md) |
| draw.io | copy the ```mermaid block below → Arrange › Insert › Advanced › Mermaid |


The `governance` package is a leaf: it imports nothing from other planned packages, and every store and every per-user read imports it. It holds three contracts. `OwnerScope` is the one place that decides whether a record with a given `owner_id` is visible to a user (owner is the user, or null for shared external content) (FR-REG-010, FR-FT-005). `Purgeable` is implemented by every store that holds user data, so deletion, "forget" and retention fan out over one interface; a new store implements `purge()` and nothing else changes (FR-STO-006, FR-PRV-002, FR-PRV-006). `Exclusion` records what a user removed from crawling, retrieval or training; it replaces the draft's separate `ForgetRule` (FR-UI-006, FR-PRV-006).

The services in `privacy` use those contracts. Models trained on deleted data are found through the dataset manifests (`DatasetStore.containing`, `ModelRegistry.trained_on`) and flagged `tainted` (FR-PRV-005).

```mermaid
classDiagram
  direction TB

  class OwnerScope {
    <<planned P2 REG-010 FT-005>>
    +user_id: str
    +for_user(user_id: str) OwnerScope$
    +allows(owner_id: str | None) bool
    +assert_all(owner_ids: Iterable[str | None]) None
  }
  class PurgeScope {
    <<planned P1 STO-006 PRV-002 PRV-006>>
    +owner_id: str | None
    +source_id: str | None
    +document_ids: list[str] | None
    +glob: str | None
    +before: datetime | None
  }
  class Purgeable {
    <<planned abstract P1 STO-006 PRV-002>>
    +store_name: str$
    +purge(scope: PurgeScope) int*
  }
  class Exclusion {
    <<planned P2 UI-006 PRV-006>>
    +user_id: str
    +document_id: str | None
    +source_id: str | None
    +glob: str | None
    +scopes: set[crawl | retrieval | training]
    +created_at: datetime
  }
  class AccountDeletionService {
    <<planned P4 PRV-002 VER-008>>
    +purgers: list[Purgeable]
    +taint: TaintTracker
    +log: DeletionLogStore
    +delete_account(user_id: str) DeletionLog
  }
  class DataExportService {
    <<planned P4 PRV-001>>
    +export(user_id: str) Path
  }
  class tools_forget {
    <<planned cli P2 PRV-006>>
    tools.forget --doc --glob
    +main() int
  }
  class DeletionLog {
    <<planned P1 PRV-002 PRV-006>>
    +id: str
    +user_id: str | None
    +scope: PurgeScope
    +requested_at: datetime
    +completed_at: datetime | None
    +stores: dict[str, int]
  }
  class DeletionLogStore {
    <<planned abstract P1 PRV-002>>
    Mongo impl: collection deletion_log
    +append(log: DeletionLog) None*
  }
  class TaintTracker {
    <<planned P4 PRV-005>>
    +datasets: DatasetStore
    +models: ModelRegistry
    +window_days: int = 30
    +on_deleted(document_ids: list[str]) list[ModelVersion]
    +overdue(now: datetime) list[ModelVersion]
  }
  class RawDataStore {
    <<abstract>>
    ref, see 4
  }
  class RegistryStore {
    <<abstract>>
    ref, see 2a
  }
  class CleanedDocumentStore {
    <<planned abstract P2>>
    ref, see 7
  }
  class VectorStore {
    <<planned abstract P2>>
    ref, see 7
  }
  class DatasetStore {
    <<planned abstract P3>>
    ref, see 8a
  }
  class ModelRegistry {
    <<planned abstract P3>>
    ref, see 8b
  }
  class ModelVersion {
    <<planned P3>>
    ref, see 8b
  }
  class Tracer {
    <<planned abstract P2>>
    ref, see 9
  }
  class SnapshotLayout {
    <<planned P4 VER-008>>
    ref, see 4
  }

  Purgeable ..> PurgeScope
  Purgeable <|-- RawDataStore : planned P1
  Purgeable <|-- RegistryStore : planned P1
  Purgeable <|-- CleanedDocumentStore
  Purgeable <|-- VectorStore
  Purgeable <|-- DatasetStore
  Purgeable <|-- ModelRegistry
  Purgeable <|-- Tracer
  AccountDeletionService "1" o-- "1..*" Purgeable
  AccountDeletionService --> TaintTracker
  AccountDeletionService --> DeletionLogStore
  AccountDeletionService ..> SnapshotLayout : user partition
  tools_forget ..> RegistryStore : add Exclusion, all scopes
  tools_forget ..> Purgeable : raw tombstone, cleaned, vectors
  tools_forget ..> DeletionLogStore
  tools_forget ..> Exclusion
  DeletionLogStore ..> DeletionLog
  DeletionLog --> PurgeScope
  TaintTracker --> DatasetStore : containing
  TaintTracker --> ModelRegistry : trained_on, tag tainted
  TaintTracker ..> ModelVersion
  DataExportService ..> RawDataStore : find owner_id
  DataExportService ..> RegistryStore
  DataExportService ..> DatasetStore
  DataExportService ..> ModelRegistry : lineage
```
