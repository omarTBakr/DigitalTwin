# 11. Exceptions

[← Class diagrams](README.md) · [Hub](../README.md) · Previous: [10b. Governance and privacy operations (planned)](10b_governance_and_privacy_operations.md)

| | |
|---|---|
| Status | Implemented, with planned additions |
| Subsystem | `llm_engineering/exceptions.py` plus planned subclasses |
| Requirements | [DS](../requirements/requirements.md#211-dataset-generation-ds) 010 · [ETL](../requirements/requirements.md#23-extraction-framework-etl) 002 · [EVAL](../requirements/requirements.md#213-evaluation-eval) 004 · [FEA](../requirements/requirements.md#210-feature-pipeline-fea) 004 · [FT](../requirements/requirements.md#212-fine-tuning-ft) 005 · [INF](../requirements/requirements.md#214-rag-inference-service-inf) 003, 005, 008 · [OPS](../requirements/requirements.md#215-llmops-monitoring-cicd-deployment-ops) 008 · [ORC](../requirements/requirements.md#26-orchestration-and-cli-orc) 006 · [REG](../requirements/requirements.md#22-source-registry-and-multi-user-reg) 010, 012 · [STO](../requirements/requirements.md#25-raw-storage-sto) 007 · [TRG](../requirements/requirements.md#28-triggers-and-scheduling-trg) 007 · [UI](../requirements/requirements.md#29-source-registration-ui-and-api-ui) 007, 009, 012 · [NFR-COST](../requirements/requirements.md#39-cost-cost) 001 |
| Use cases | none |
| Sequence diagrams | none |
| draw.io | copy the ```mermaid block below → Arrange › Insert › Mermaid |


Every intentional error derives from `DigitalTwinError`. Item-level `ParseError` is logged and skipped. Source-level `SourceError` fails one source. `AccessBlockedError`, `AuthenticationError` and `RateLimitError` stop the provider. `ConfigError` stops before fetching (FR-ETL-002). Planned subclasses go under the branch whose handling policy they share. Three new branches are added for budgets, access control and inference. `OwnerIsolationError` is raised by `OwnerScope.assert_all` when another owner's data reaches a user scope (FR-REG-010, FR-FT-005).

```mermaid
classDiagram
  direction LR

  class DigitalTwinError {
    Exception
  }
  class ConfigError {
    +path: Path | None
    +ConfigError(message: str, *, path: Path | None)
  }
  class ConfigNotFoundError
  class ConfigParseError
  class ConfigValidationError
  class UnknownSourceError
  class UnknownUserError
  class SourceError {
    +source: str | None
    +SourceError(message: str, *, source: str | None)
  }
  class SourceUnavailableError
  class RateLimitError {
    +retry_after: float | None
    +RateLimitError(message: str, *, source: str | None, retry_after: float | None)
  }
  class AccessBlockedError
  class AuthenticationError
  class ParseError {
    +item: str | None
    +ParseError(message: str, *, source: str | None, item: str | None)
  }
  class StorageError
  class StorageUnavailableError
  class RegistryError
  class StoreCorruptedError {
    +location: str
    +StoreCorruptedError(message: str, *, location: str)
  }
  class VersioningError
  class PipelineError

  class OwnershipConflictError {
    <<planned P1 REG-012>>
    +existing_owner: str
    +claimant: str
  }
  class LockHeldError {
    <<planned P1 ORC-006>>
    +key: str
    +holder_run_id: str
  }
  class VectorStoreError {
    <<planned P2 FEA-004>>
  }
  class DatasetQualityError {
    <<planned P3 DS-010>>
  }
  class PromotionRejectedError {
    <<planned P3 EVAL-004>>
  }
  class BudgetExceededError {
    <<planned P2 OPS-008 NFR-COST-001>>
    +stage: str
    +budget_usd: float
  }
  class AccessError {
    <<planned P2 INF-005 UI-009>>
  }
  class UnauthenticatedError {
    <<planned P2 INF-005>>
    HTTP 401
  }
  class PermissionDeniedError {
    <<planned P4 UI-007 INF-005>>
    HTTP 403
  }
  class QuotaExceededError {
    <<planned P2 UI-012 INF-008>>
    HTTP 429
  }
  class OwnerIsolationError {
    <<planned P2 REG-010 FT-005>>
  }
  class WebhookSignatureError {
    <<planned P4 TRG-007>>
  }
  class InferenceError {
    <<planned P2 INF-003>>
  }
  class ModelUnavailableError {
    <<planned P3 INF-003>>
  }

  DigitalTwinError <|-- ConfigError
  DigitalTwinError <|-- SourceError
  DigitalTwinError <|-- StorageError
  DigitalTwinError <|-- VersioningError
  DigitalTwinError <|-- PipelineError
  ConfigError <|-- ConfigNotFoundError
  ConfigError <|-- ConfigParseError
  ConfigError <|-- ConfigValidationError
  ConfigError <|-- UnknownSourceError
  ConfigError <|-- UnknownUserError
  SourceError <|-- SourceUnavailableError
  SourceError <|-- AuthenticationError
  SourceError <|-- ParseError
  SourceUnavailableError <|-- RateLimitError
  SourceUnavailableError <|-- AccessBlockedError
  StorageError <|-- StorageUnavailableError
  StorageError <|-- RegistryError
  StorageError <|-- StoreCorruptedError

  ConfigError <|-- OwnershipConflictError
  PipelineError <|-- LockHeldError
  StorageError <|-- VectorStoreError
  PipelineError <|-- DatasetQualityError
  PipelineError <|-- PromotionRejectedError
  DigitalTwinError <|-- BudgetExceededError
  DigitalTwinError <|-- AccessError
  AccessError <|-- UnauthenticatedError
  AccessError <|-- PermissionDeniedError
  AccessError <|-- QuotaExceededError
  AccessError <|-- WebhookSignatureError
  AccessError <|-- OwnerIsolationError
  DigitalTwinError <|-- InferenceError
  InferenceError <|-- ModelUnavailableError

  note for StoreCorruptedError "planned STO-007: also raised for an unknown higher schema_version"
```
