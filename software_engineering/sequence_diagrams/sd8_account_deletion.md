# SD-8. Account deletion (planned P4)

[← Sequence diagrams](README.md) · [Hub](../README.md) · Previous: [SD-7](sd7_register_source_ui.md)

| | |
|---|---|
| Status | Planned P4 |
| Requirements | [PRV](../requirements/requirements.md#216-privacy-and-data-subject-operations-prv) 002, 005 · [VER](../requirements/requirements.md#27-data-versioning-ver) 008 |
| User stories | US-045, US-093, US-095 ([backlog](../user_stories/user_stories.md)) |
| Use cases | [UC-23](../use_cases/06_admin_privacy_ops.md#uc-23-delete-my-account) |
| Class diagrams | [2a](../class_diagrams/02a_registry_core.md), [4](../class_diagrams/04_raw_storage_and_versioning.md), [7](../class_diagrams/07_feature_pipeline.md), [8a](../class_diagrams/08a_dataset_generation.md), [8b](../class_diagrams/08b_training_model_registry_and_evaluation.md), [9](../class_diagrams/09_llm_clients_inference_and_llmops.md), [10a](../class_diagrams/10a_ui_api_and_authentication.md), [10b](../class_diagrams/10b_governance_and_privacy_operations.md) |
| draw.io | copy the ```mermaid block below → Arrange › Insert › Advanced › Mermaid |


PRV-002, PRV-005, VER-008, NFR-CMP-006. Every store that holds user data implements `Purgeable`; the deletion completes across all of them or is logged as incomplete.

```mermaid
sequenceDiagram
  autonumber
  actor User
  participant Api as ApiApp
  participant Del as AccountDeletionService
  participant RegStore as RegistryStore
  participant Raw as RawDataStore
  participant Cds as CleanedDocumentStore
  participant VS as VectorStore
  participant DStore as DatasetStore
  participant MReg as ModelRegistry
  participant Tracer as Tracer
  participant Snap as SnapshotLayout
  participant Taint as TaintTracker
  participant Log as DeletionLogStore

  User->>Api: DELETE /api/v1/me (re-authenticated)
  Api->>Del: delete_account(user_id)
  Del->>RegStore: disable user (no new runs select their sources)
  critical purge every store by PurgeScope(owner_id=user)
    Del->>VS: purge(scope)
    Del->>Cds: purge(scope)
    Del->>Raw: purge(scope)
    Del->>DStore: purge(scope)
    Del->>MReg: purge(scope) (the user's adapters)
    Del->>Tracer: purge(scope)
    Del->>RegStore: purge(scope): subscriptions, owned sources, user record
  option a store fails
    Del->>Log: append(DeletionLog incomplete, failed stores) and retry within 7 days
  end
  Del->>Snap: user partition path (data/raw/users/<id>/): removed from the next snapshot
  Del->>Taint: on_deleted(document ids)
  Taint->>MReg: trained_on(datasets containing the documents)
  Taint->>MReg: tag(shared models, tainted) (retrain or retire within 30 days)
  Del->>Log: append(DeletionLog completed, stores[])
  Del-->>Api: DeletionLog
  Api-->>User: 202 deletion completed or scheduled
  Note over Snap: past snapshots in git and DVC history follow the policy decided in OQ-06
```
