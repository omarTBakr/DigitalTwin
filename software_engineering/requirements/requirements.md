# DigitalTwin: Software Requirements Specification

| | |
|---|---|
| Document status | v1.0, finalized from Draft v0.1 after principal review; for owner approval |
| Date | 2026-10-23 |
| Baseline | `main` at `264cc1c` (ETL stage complete; later stages not started). Updated for `4c40ca7` (NFR-PRIV-002) and for entities introduced by [`class_diagram.md`](../class_diagrams/README.md) (section 5.2). |
| Owner | Omar Ayman Bakr |
| Reference | *LLM Engineer's Handbook* (Iusztin & Labonne). The book's stages are followed; its architecture is not copied. |
| Review | [`requirements_review.md`](../reviews/requirements_review.md) lists every change from the draft and the reason for it. |

**Status legend** (applies to every requirement)
- **Implemented**: the behaviour exists in code at the baseline commit and was checked by reading that code. Each one names the module that implements it.
- **Implemented (unverified)**: the code exists and was read, but it has never run against real input.
- **Partial**: some of the behaviour exists. The gap is stated.
- **Planned**: no code exists yet. The requirement records intent and the acceptance criteria to build against.
- **Withdrawn**: retired (duplicate or superseded). The ID is kept so it is never reused.

**Priority legend** (MoSCoW, per functional requirement): **Must** (the phase cannot exit without it), **Should** (important, can slip one phase), **Could** (nice to have), **Won't-now** (explicitly out of the current plan; kept for the record).

**Release / phase legend**

| Phase | Scope | Exit criteria |
|---|---|---|
| **P0** | ETL as built at `264cc1c` | Done. All *Implemented* FRs below. |
| **P1** | ETL hardening and triggers | Tests and CI green (FR-OPS-003, NFR-MNT-002). Incremental crawl, tombstones and change flags work (FR-REG-011, FR-ETL-010, FR-STO-005). An unattended scheduled run completes with no human in the loop (FR-MED-008, FR-TRG-002). Compliance gaps closed (FR-ART-002/003, NFR-CMP-002). |
| **P2** | Feature pipeline and RAG | Cleaned docs, chunks and vectors are built incrementally from ETL change sets. A token-protected RAG API answers with citations, and its retrieval and generation are evaluated (FR-EVAL-003). |
| **P3** | Datasets, fine-tuning, evaluation | Versioned instruction and preference datasets. SFT and DPO adapters with lineage. An eval-gated promotion step. |
| **P4** | UI, multi-user and LLMOps | Authenticated multi-user UI and API, per-user isolation proven by tests, CD with rollback, monitoring and alerts, data-subject operations. |

Verification note: all *Implemented* claims were checked by reading code only. Nothing was run. The repo has no automated tests (there is no `tests/` directory), so no claim is backed by a test yet. See NFR-MNT-002.

---

## 1. Introduction

### 1.1 Purpose
This document states what the DigitalTwin system must do, from data collection to a deployed RAG and fine-tuned model. It also records which parts exist today, how important each requirement is, and in which phase it is delivered. It is the basis for design decisions in the stages that are not built yet, and for the acceptance tests of each stage.

### 1.2 Product summary
DigitalTwin is an "LLM twin". It is a language model system that:
1. writes in the owner's voice (style learned from the owner's own writing: notes, code, posts), and
2. answers from the owner's knowledge (retrieval over the owner's writing plus curated external material).

The system is a chain of pipelines:

```
sources ─► ETL (raw_documents + registry) ─► DVC raw snapshot (data_md5)
                │ change set (new / changed / deleted ids)
                ▼
        feature pipeline (clean ─► chunk ─► embed ─► vector DB)
                │                                   │
                ├─► dataset generation (instruction + preference) ─► dataset versions
                │        └─► fine-tuning (SFT ─► DPO) ─► model registry ─► eval gate
                │                                                         │
                └──────────────────────► RAG inference API ◄──────────────┘
                                               │
                              tracing / monitoring / feedback / CI/CD
```

Section 9 maps each requirement group to these stages and lists the end-to-end chains (lineage, deletion, exclusion, isolation, cost) that cross stage boundaries.

### 1.3 Goals
- G1: Collect the owner's own writing and selected external knowledge from multiple platforms. Collection must be repeatable and idempotent, and must follow each platform's terms.
- G2: Keep a clean split between **self** content (style and voice) and **external** content (knowledge only). The split must hold through every later stage.
- G3: Produce versioned, reproducible datasets and models. Any model must be traceable to the data snapshot and code that produced it.
- G4: Serve a RAG-backed twin through an API with measured quality, latency and cost.
- G5: Grow from one user (the owner) to several users. Each user registers their own sources, and a shared source is ingested once.
- G6: Make ingestion event-driven, so that new content (for example a new post) reaches the twin without a manual full run.
- G7: Keep spend bounded. Every paid resource (LLM API, GPU, hosting) has a configured budget with a hard stop.

### 1.4 Non-goals
- NG1: Bypassing paywalls, logins, member-only content, CAPTCHAs or other bot defences. Scraping platforms whose terms forbid it. This includes a human solving a bot challenge inside a crawler session.
- NG2: Training a foundation model from scratch. Only fine-tuning of open-weight base models is in scope.
- NG3: A public, anonymous, multi-tenant SaaS. "Multi-user" means a small set of known, authenticated, invited users.
- NG4: Impersonating the owner to third parties without disclosure, such as auto-posting to social platforms as the owner.
- NG5: Real-time streaming ingestion (sub-minute latency). Event triggers with minute-to-hour latency are enough.
- NG6: Redistributing third-party content collected as external knowledge.

### 1.5 Stakeholders and actors

| Actor | Type | Interest / interactions |
|---|---|---|
| **Owner** (Omar) | Primary user, operator, developer | Declares sources, runs pipelines, reviews data quality, trains and evaluates models, uses the twin. Today also the only admin. |
| **Future user** | Human, authenticated, invited | Registers their own sources through a UI, subscribes to shared external sources, queries their own twin. Sees only their own data and twin. |
| **Admin** | Human role (initially the owner) | Manages users, global topics and provider settings. Disables abusive or broken sources. Handles deletion requests. |
| **Scheduler / trigger system** | System actor | Starts pipelines on a schedule, on platform events (webhooks or feed polling), or on user action. Calls the ETL with `source_ids`. |
| **Pipeline orchestrator** (ZenML) | System actor | Runs steps, tracks runs and artifacts, shows dashboards. |
| **External platforms** | External systems | Medium (RSS feeds, tag pages), GitHub REST API and raw content host, LinkedIn (official data export only), web article hosts, local Obsidian vault filesystem. Later: LLM APIs for dataset generation and judging, model hubs, GPU or cloud providers. |
| **Third-party authors** | Indirect stakeholders | Their content is collected as external knowledge. They have interests in attribution, licensing and non-redistribution. |
| **Twin consumers** | Human | People who read the twin's output (for example a recruiter chatting with the twin). They need disclosure that the answer is AI-generated. |

---

## 2. Functional requirements

Requirement IDs are stable. New requirements get new IDs at the end of their group, and retired IDs are marked **Withdrawn** and not reused.

Subsystem prefixes: CFG (configuration and topics), REG (source registry and multi-user), ETL (extraction framework), MED / GH / LI / OBS / ART (providers), STO (raw storage), ORC (orchestration and CLI), VER (data versioning), TRG (triggers and scheduling), UI (source registration UI and API), FEA (feature pipeline), DS (dataset generation), FT (fine-tuning), EVAL (evaluation), INF (RAG inference), OPS (LLMOps: monitoring, CI/CD, deployment), PRV (privacy and data-subject operations).

### 2.1 Configuration and topics (CFG)

| ID | Requirement | Acceptance criteria | Status | Priority | Phase |
|---|---|---|---|---|---|
| FR-CFG-001 | The system shall define topics in one file, `configs/topics.yaml`. Each topic maps to Medium tags and Obsidian tag prefixes. | Every topic key a source spec references is validated against `topics.yaml`. An unknown key fails loading with an error naming the key and the file (`BaseSourceSpec._check_topics`, with the topics passed as validation context by `YamlLoader.load_specs`). | Implemented | Must | P0 |
| FR-CFG-002 | The system shall load per-user declarations from `configs/users/<id>/profile.yaml` and `configs/users/<id>/sources/*.yaml`. Each declaration is validated against a discriminated union of source specs keyed by `type`. | An unknown `type`, an extra field (`extra="forbid"`), an invalid value, or a profile `id` that differs from its folder name raises a `ConfigError` subclass before any network access (`sync_registry` is the first pipeline step). | Implemented | Must | P0 |
| FR-CFG-003 | The system shall reject a user declaration that lists the same canonical source twice. | A duplicate key raises a validation error that lists the duplicate keys (`UserDeclaration._no_duplicate_sources`). | Implemented | Must | P0 |
| FR-CFG-004 | The system shall read secrets and environment settings only through one `Settings` object (`MONGO_*`, `GITHUB_*`, `DVC_*`, `RAW_STORE_*`). Real environment variables override `.env`, which overrides defaults. | `get_settings()` is the only reader of the environment in project code (no `os.environ` or `getenv` elsewhere). An invalid value (for example `MONGO_PORT=abc`) raises `ConfigValidationError`. Secrets are typed `SecretStr`. | Implemented | Must | P0 |
| FR-CFG-005 | The system shall keep provider tuning (delays, caps, retries, browser options) in `configs/providers/<provider>.yaml`, separate from user declarations. Every declared setting shall be read by code. | Changing `limit_per_topic` in `medium.yaml` changes behaviour with no code change. A unit test asserts that every field of each `*Settings` model is referenced by its provider. | Partial. Separation is implemented. `MediumSettings.skip_member_only` is declared and set in `medium.yaml` but never read; member-only stories are always skipped. Remove the key or honour it (it must not be settable to `false`, see NG1). | Should | P1 |
| FR-CFG-006 | The system shall provide a health-check tool that validates all configuration and probes each provider, with an offline mode. | `tools/validate_sources.py` exits 1 on invalid config or an unhealthy provider. `--offline` makes no network calls. Writes `data/manifests/source_health.json`. Needs no MongoDB. | Implemented (the module docstring says it "opens Medium in Chrome"; the code only fetches one author feed. Fix the docstring.) | Should | P0 |
| FR-CFG-007 | Topic definitions shall be versioned with the data they label. Renaming or removing a topic shall migrate or flag the documents that carry it. | A removed topic key that still appears on stored documents is reported by the health check. A rename declared as `renamed_from` in `topics.yaml` is applied to stored documents by a migration command. | Planned | Should | P2 |
| FR-CFG-008 | Once the UI exists, the registry shall be the single source of truth for declarations. YAML shall become a bootstrap and import path that never overwrites records created or edited through the UI or API. | Every source and subscription records `declared_via ∈ {yaml, ui, api}`. `sync_registry` updates only `yaml` records. Editing a UI-created source and then running the ETL leaves the edit intact. | Planned. Today `sync_registry` runs on every ETL run and `$set`s all declaration fields from YAML. | Must | P4 |

### 2.2 Source registry and multi-user (REG)

| ID | Requirement | Acceptance criteria | Status | Priority | Phase |
|---|---|---|---|---|---|
| FR-REG-001 | The system shall store each source once, under a canonical key, however many users declare it. | Two users declaring `medium_tag: RAG` and `medium_tag: rag` produce one `sources` record `medium:tag:rag` and two `subscriptions` (`registry/keys.py`, `RegistrySeeder`). How the two declarations are merged is FR-REG-013. | Implemented | Must | P0 |
| FR-REG-002 | Canonical keys shall normalise equivalent inputs. URLs: lower-cased scheme and host, no fragment, no trailing `/`, tracking parameters (`utm_*`, `mc_*`, `fbclid`, `gclid`, `ref`, `source`) removed, query sorted. Handles and tags: trimmed and lower-cased. Medium handles get an `@` prefix. | `article_key("https://X.com/a/?utm_source=t#h") == article_key("https://x.com/a")`. Known limits, accepted: `http`/`https` and `www.`/bare host are distinct keys. | Implemented | Must | P0 |
| FR-REG-003 | The system shall model users (`id`, `name`, `handles`), sources and many-to-many subscriptions. Uniqueness of `(user_id, source_id)` shall be enforced in storage. | A unique index exists on `subscriptions(user_id, source_id)` (`MongoRegistryStore.setup`). | Implemented | Must | P0 |
| FR-REG-004 | Sources holding a user's own writing (GitHub, Obsidian, LinkedIn) shall carry `owner_id`. External sources (Medium, articles) shall be shared and carry no owner. | `Source.from_spec` sets `owner_id` only when `spec.owned` is true. Conflicting ownership claims are FR-REG-012. | Implemented | Must | P0 |
| FR-REG-005 | Seeding the registry from declarations shall be idempotent. | Running `sync_registry` twice with unchanged YAML reports `sources_new=0`, `subscriptions_new=0` on the second run. Crawl `state` is never overwritten by seeding (`$setOnInsert`). | Implemented | Must | P0 |
| FR-REG-006 | The registry shall keep the latest crawl state for each source: status (`never`/`ok`/`failed`), last run id, timestamp, error, and item counts. | After a run, every crawled source has `state.last_run_id` equal to that run's id (`steps/etl/crawl.py:record_states`). | Implemented | Must | P0 |
| FR-REG-007 | Selecting sources for a run shall support three modes: all enabled sources; one user's subscribed enabled sources; an explicit list of source ids (optionally checked against a user's subscriptions). An explicitly requested source that is disabled shall be reported, not dropped silently. | An unknown user raises `UnknownUserError`. An unknown source id, or one the user is not subscribed to, raises `UnknownSourceError` before crawling (`SourceSelector`). An explicitly requested disabled source appears in the selection log as `skipped: disabled`. | Partial. The three modes are implemented. Explicitly requested disabled sources are filtered out with no message. | Should | P1 |
| FR-REG-008 | A user shall be able to unsubscribe from a source. A shared source with no subscribers left shall be disabled, and its documents kept or purged according to FR-PRV-003. | After the last unsubscribe the source has `enabled=false` and is not selected by any run. | Planned. The seeder only upserts; a source removed from YAML stays in the registry. | Should | P1 |
| FR-REG-009 | Removing a source from a user's YAML (or, later, the UI) shall be applied to the registry: the subscription is deleted, and the source is not left stale. The same applies to a removed user folder. | Sync reports `subscriptions_removed=n` (and `users_removed`), and the selector no longer returns the source for that user. | Planned | Should | P1 |
| FR-REG-010 | The system shall support several users with isolated own-content. A user's `self` documents, datasets, adapters and twin shall never be visible to, or trained into, another user's twin. | A query for user B's twin never retrieves a document with `owner_id=A`. Dataset builds filter by `owner_id`. An automated isolation test with two seeded users runs in CI. | Partial. `owner_id` exists on documents and sources; nothing enforces isolation yet, and FR-REG-012 is a precondition. | Must | P2 (retrieval), P3 (datasets) |
| FR-REG-011 | The system shall skip re-ingesting a source whose content has not changed since its last successful crawl, where the platform allows change detection (ETag or `Last-Modified`, `pushed_at` and blob SHA, feed GUIDs, file mtime and hash). | A second run with no upstream changes performs no full-content fetches for GitHub files whose blob SHA is unchanged and no writes for unchanged Obsidian notes. The report shows them as `skipped: unchanged`. Uses the cursors of FR-REG-014. | Partial. Documents dedupe by stable id, and Medium skips documents already stored for the same topics (the feed is still fetched). GitHub, Obsidian and articles re-fetch everything on each run. `content_hash` is stored but not used to skip work. | Must | P1 |
| FR-REG-012 | An owned source shall have exactly one owner. A declaration that would change the `owner_id` of an existing owned source shall be rejected, not applied. | User B declaring `github: omarTBakr` when `github:user:omartbakr` is owned by `omar` fails sync with `OwnershipConflictError` naming both users; the stored `owner_id` is unchanged. Proving account ownership is FR-UI-011. | Planned. Today `upsert_source` `$set`s `owner_id`, so the last user seeded becomes the owner of a shared GitHub key, and its code would become that user's `self` data. | Must | P1 |
| FR-REG-013 | When several users subscribe to one shared source, the source record shall merge their declarations deterministically: topics = union of all subscribers' topics; `enabled` = true if any subscriber has it enabled; per-subscriber choices (topic interest) live on the subscription; conflicting crawl-shaping fields are rejected. | Two users declaring `medium_author @x` with topics `[rag]` and `[llms]` give a source with topics `[llms, rag]`, whatever the seeding order. One user setting `enabled: false` does not disable the source for the other. | Planned. Today the last user seeded wins for `spec`, `topics` and `enabled`. | Must | P1 |
| FR-REG-014 | The crawl state shall keep, besides the latest outcome: `last_success_at`, `last_success_run_id`, `consecutive_failures`, a provider-specific incremental cursor (for example ETag, `pushed_at` per repo, last feed GUID, vault mtime watermark), and `retry_not_before` from a `RateLimitError.retry_after` or a blocked-access cool-down. | A failed run leaves `last_success_at` and the cursor unchanged. `retry_not_before` is set when a provider stops with `RateLimitError(retry_after=…)`. Used by FR-REG-011, FR-TRG-006, FR-OPS-006 and FR-UI-003. | Planned. `SourceState` is overwritten as a whole by each run, and `retry_after` is lost (only the message string is stored). | Must | P1 |

### 2.3 Extraction framework (ETL)

| ID | Requirement | Acceptance criteria | Status | Priority | Phase |
|---|---|---|---|---|---|
| FR-ETL-001 | Every provider shall implement one abstract extractor contract: an optional shared `session()`, `extract_source(source)` yielding `RawDocument`s, and `health_check(offline)`. | `BaseExtractor` subclasses exist for medium, github, linkedin, obsidian and articles, registered in `raw_data/sources/registry.py`. | Implemented | Must | P0 |
| FR-ETL-002 | Errors shall be isolated by level. An item-level error is recorded and skipped. A source-level `SourceError` marks that source failed and the run continues with the next source. `AccessBlockedError`, `AuthenticationError` and `RateLimitError` stop the provider and mark the remaining sources "not crawled". `ConfigError` stops before fetching. A provider may handle a provider-wide error itself only where a requirement says so (FR-MED-003). | Error handling in `BaseExtractor.extract` and `_abort`. A source whose every attempted item failed is marked failed (`_fail_sources_without_successes`). Errors that are not `SourceError` are FR-ETL-012. | Implemented | Must | P0 |
| FR-ETL-003 | Every crawl shall produce a `CrawlReport` with one outcome per item (`ok`/`failed`/`skipped` plus a reason) and one error per failed source. | The report is rendered as HTML per provider in the ZenML dashboard (`steps/etl/html_report.py`). | Implemented | Must | P0 |
| FR-ETL-004 | Every document shall conform to one `RawDocument` contract: stable `id` (`{source}:{native_id}`), `provider`, `source` kind, `owner_id`, `source_ids`, `origin` (`self`/`external`), `title`, markdown `content`, `url`, `author`, `created_at`/`updated_at`, `content_hash` (sha256), `topics`, `provenance[]`, `metadata`. | All extractors build documents through `BaseExtractor.make_document`. | Implemented | Must | P0 |
| FR-ETL-005 | Third-party material found inside a user's own source (for example PDFs in the vault) shall be marked `origin=external` and get no `owner_id`. | Obsidian PDFs use `pdf_origin` (default `external`), and `make_document(owned=False)` drops `owner_id`. | Implemented | Must | P0 |
| FR-ETL-006 | Each document shall record provenance: source id, query or page, rank, run id, and collection time. The last 50 sightings are kept. | `$push` with `$slice: -50` on upsert. | Implemented | Must | P0 |
| FR-ETL-007 | Topic assignment shall combine declared source topics, platform tags mapped through `topics.yaml`, and path or repo glob rules. | Medium: tag-source topics plus mapped tags. Authors: mapped tags intersected with followed topics (all followed topics if none map). Obsidian: tag prefixes plus `topic_rules`. GitHub: repo topics and language mapped, plus `topic_rules` on repo name. LinkedIn: hashtags mapped. | Implemented | Should | P0 |
| FR-ETL-008 | Per-topic caps (`limit_per_topic`, default 100) shall hold across runs for capped providers. Counts already in the store count toward the cap. | A Medium run with every topic of a source at cap records `skipped: topics [...] already at cap` and fetches nothing for that source. Whether other providers are capped is OQ-12. | Implemented (Medium only) | Should | P0 |
| FR-ETL-009 | Documents shall be written in batches of 50 during extraction, and the open batch shall be flushed when extraction stops for any reason, so that only a hard kill of the process can lose data (at most one batch). | `BATCH_SIZE=50` and `finally: flush()` in `steps/etl/crawl.py`. | Implemented | Must | P0 |
| FR-ETL-010 | Content that disappears upstream (a deleted or renamed note, repo, file or export item) shall be detected and marked `deleted_at` (a tombstone), not left as live data. Deletion shall be inferred only from a **complete** enumeration of a source (Obsidian vault, GitHub repo tree that is not truncated, LinkedIn export). It shall never be inferred from capped or windowed listings (Medium feeds and tag pages, which show only recent items). | After a note is deleted from the vault, the next successful run marks its document deleted. A failed or truncated crawl tombstones nothing. A Medium article missing from a feed is never tombstoned. The feature pipeline excludes tombstoned documents and removes their vectors (FR-FEA-005). | Planned | Must | P1 |
| FR-ETL-011 | Near-duplicate content reachable under different ids (the same article via two URLs or a feed and a page, or a README mirrored in docs) shall be detected by `content_hash` (exact) and MinHash (near, Jaccard ≥ 0.9 by default). | A dedup report lists groups that share `content_hash` or exceed the near-duplicate threshold. Downstream stages use one representative per group. | Planned | Should | P2 |
| FR-ETL-012 | An unexpected exception (one that is not a `SourceError`, for example a `KeyError` from a changed API payload) inside one source shall be contained like a source-level error: logged with its traceback, the source marked failed, and the provider continues. Only `ConfigError` and `StorageError` may end a crawl step. | A fault-injection test makes one GitHub source raise `KeyError`. The other sources of the provider and the other providers still run, `version_raw_data` and `summarize_crawl` still run, and the run ends with `PipelineError` naming the failed source. | Planned. Today such an exception escapes `crawl_provider`, fails the ZenML step, and the later steps (other providers, versioning, summary) do not run. | Must | P1 |
| FR-ETL-013 | Topics derived from rules and tags shall be recomputed on each crawl of a document's source and shall replace the previous derived topics for that source, so that a corrected rule or topic mapping also removes wrong topics. Topics contributed by other sources of the same document are kept. | After removing a `topic_rules` entry and re-running, affected documents no longer carry that topic. A Medium article found by two tags keeps both tags' topics. | Planned. `upsert` merges `topics` with `$addToSet`, so topics can be added but never removed. This also inflates per-topic cap counts. | Should | P1 |

### 2.4 Providers

#### Medium (MED)
| ID | Requirement | Acceptance criteria | Status | Priority | Phase |
|---|---|---|---|---|---|
| FR-MED-001 | Article text shall come only from Medium's official RSS feeds (author or publication). Article pages shall not be scraped. | `MediumFeedClient` is the only source of `content`. | Implemented | Must | P0 |
| FR-MED-002 | Member-only stories (the feed has a preview only) shall always be skipped, even when the crawler profile is logged in. This shall not be configurable. | Outcome: `skipped: member-only story` whenever the feed entry has no full content (`MediumExtractor._accept`). | Implemented (the behaviour is hard-coded; the `skip_member_only` setting is dead, see FR-CFG-005) | Must | P0 |
| FR-MED-003 | `medium_tag` sources may discover the tag's top article links with a browser at human pace, **only in interactive mode** (FR-MED-008). If a bot challenge does not clear on its own, discovery shall fall back to the tag's RSS feed for the rest of the run. No person shall solve a challenge for the crawler. | `listing_blocked` flag in `MediumExtractor._discover`. With `interactive=false` the browser is never started. | Implemented, on compliance hold. The fallback works, but `medium.yaml` sets `headless: false` and the browser waits 30 s so a person can click the check (see RISK-01, OQ-01, NFR-CMP-002). | Could | P0 (hold: P1 decision) |
| FR-MED-004 | `medium_author` sources shall read the author's feed with no browser. | The browser is started only if a `medium_tag` source is selected. | Implemented | Must | P0 |
| FR-MED-005 | Feed requests shall be paced (`feed_delay_s`, default 3 s) and back off on HTTP 429 and 5xx, honouring `Retry-After` when present, up to `feed_max_retries`. Exhausted retries on 429 shall raise `RateLimitError` (with `retry_after`) and stop the provider, wherever the feed is fetched. Exhausted retries on 5xx shall raise `SourceUnavailableError`. | `feed_client.py`. A test with a mock server returning 429 on an article-lookup feed stops the provider after the retries. | Partial. Pacing and exponential backoff are implemented. `Retry-After` is ignored. 5xx exhaustion is raised as `RateLimitError`. `_find_in_feed` catches every `SourceError`, including `RateLimitError`, records the item failed and continues, so a throttled tag crawl keeps hitting Medium. | Must | P1 |
| FR-MED-006 | Articles found on a tag page but missing from the author's feed (older than about the last 10 posts) shall be recorded as skipped with that reason. | Outcome reason `not in <feed> (feeds carry only the latest ~10 posts)`. | Implemented | Should | P0 |
| FR-MED-007 | The owner's own Medium posts (if any) shall be ingested as `origin=self` with `owner_id`. | A `medium_author` spec flagged `own: true` produces `self` documents with the declaring user's `owner_id`, subject to FR-REG-012. | Planned. All Medium content is `external` today. | Could | P1 |
| FR-MED-008 | The ETL shall have an unattended mode (the default for scheduled and triggered runs) in which Medium discovery uses only official RSS (author, publication and tag feeds) and no browser is started. | With `interactive=false` (default), a run on a headless machine with no display completes with no browser process and no waits for human input. | Planned | Must | P1 |

#### GitHub (GH)
| ID | Requirement | Acceptance criteria | Status | Priority | Phase |
|---|---|---|---|---|---|
| FR-GH-001 | The system shall ingest README, markdown, Python and notebook files from a user's public repositories (repo list and trees through the GitHub REST API, file bodies from `raw.githubusercontent.com`), with include/exclude globs, fork and hidden-path filters, a size limit (`max_file_kb`) and a minimum length (`min_chars`). | `GitHubExtractor`, `github/files.py`. | Implemented | Must | P0 |
| FR-GH-002 | Notebooks shall be converted to markdown (markdown and code cells, no outputs). | `github/notebook.py`. | Implemented | Must | P0 |
| FR-GH-003 | An optional token shall raise rate limits. Exhausted limits (403/429 with `X-RateLimit-Remaining: 0`) shall raise `RateLimitError` with `retry_after`. | `github/client.py`. Secondary rate limits (403 with `Retry-After` but remaining > 0) are today treated as a repo failure; FR-REG-014 stores `retry_after`. | Implemented | Must | P0 |
| FR-GH-004 | Truncated repository trees shall be logged as a warning and recorded in the crawl report. A truncated tree shall disable deletion inference for that repo (FR-ETL-010). | Warning text "file tree truncated". | Partial. The warning is logged only; nothing is recorded in the report. | Could | P1 |
| FR-GH-005 | Unchanged files shall not be re-downloaded (compare blob SHA with the stored metadata; skip a whole repo whose `pushed_at` is unchanged). | See FR-REG-011. The blob SHA is stored in `metadata.sha`. | Planned | Must | P1 |
| FR-GH-006 | Only content the user authored shall count as `self`. Vendored or third-party code inside repos shall be excludable, and shall be detected by a configurable list of vendored paths and a licence-header heuristic. | A vendored file is either excluded or ingested as `external`. The crawl report counts files reclassified by the heuristic. | Partial. Exclusion is by glob only. | Should | P2 |
| FR-GH-007 | With a token, the user's private repositories shall be ingestible when the user opts in. | Opt-in `include_private: true` lists repos from `/user/repos` with the user's token. Without opt-in no private repo is read. | Planned. `.env.example` says the token is "needed for private repos", but the code calls `/users/{u}/repos`, which returns public repos only. Fix the comment now. | Could | P4 |

#### LinkedIn (LI)
| ID | Requirement | Acceptance criteria | Status | Priority | Phase |
|---|---|---|---|---|---|
| FR-LI-001 | LinkedIn content shall be ingested only from the user's official data export, unzipped to `export_dir`. LinkedIn shall never be scraped. | `LinkedInExportSpec`, `linkedin/export_files.py`. | Implemented | Must | P0 |
| FR-LI-002 | Posts, articles and comments shall be parsed into `linkedin_post`, `linkedin_article` and `linkedin_comment` documents (`origin=self`), with hashtags mapped to topics. | `linkedin/parsers.py`. A fixture test with a redacted real export passes before status becomes Implemented. | Implemented (unverified): never run on real data (export pending). | Must | P0 (verify in P1) |
| FR-LI-003 | A missing export directory shall fail only that source, with a clear message. | `SourceUnavailableError` names the path. | Implemented | Must | P0 |
| FR-LI-004 | A user shall be able to upload a LinkedIn export zip through the UI. The system unpacks it to the user's export directory and triggers ingestion. | Upload, then the run starts within 1 minute. The zip is deleted after extraction. Zip-slip paths and archives over a size limit are rejected. | Planned | Should | P4 |

#### Obsidian (OBS)
| ID | Requirement | Acceptance criteria | Status | Priority | Phase |
|---|---|---|---|---|---|
| FR-OBS-001 | The system shall ingest notes from a local vault with include, exclude and hidden-path globs, a minimum length, and markdown cleanup (embeds dropped, wikilinks reduced to their text). | `ObsidianExtractor`, `obsidian/markdown.py`. | Implemented | Must | P0 |
| FR-OBS-002 | PDFs matching `pdf_include` shall be extracted (PyPDF) as `external` by default, with a size limit (`pdf_max_mb`). | `_pdf_document`. | Implemented | Must | P0 |
| FR-OBS-003 | A missing vault shall fail only that source. | `SourceUnavailableError("vault not found")`. | Implemented | Must | P0 |
| FR-OBS-004 | Private or sensitive notes shall be excludable by glob, and also by a frontmatter flag (`twin: false` or `private: true`). | A note with `private: true` is skipped with reason `private`, and an already stored copy is tombstoned on the next run. | Partial. Glob exclusion only (for example `images/Vodafone*`). | Must | P1 |
| FR-OBS-005 | Obsidian ingestion shall run only on the machine that holds the vault. Remote or multi-user setups shall need an explicit upload or sync mechanism. | See FR-UI-005. A run on a machine without the vault fails only that source (FR-OBS-003). | Planned | Should | P4 |
| FR-OBS-006 | One unreadable note shall fail only that note, not the whole vault. | A vault containing one file with invalid UTF-8 or broken frontmatter yields every other note, and the bad file is reported as `failed` with its path. | Planned. `ObsidianVault.notes()` reads the vault in one `ObsidianLoader` pass, so one bad file raises `SourceUnavailableError` for the whole vault (documented in the code). | Should | P1 |

#### Articles (ART)
| ID | Requirement | Acceptance criteria | Status | Priority | Phase |
|---|---|---|---|---|---|
| FR-ART-001 | The system shall ingest single public web pages by URL (plain HTTP, no JavaScript) and convert them to markdown. Pages below `min_chars` (default 200) fail the source. | `CustomArticleCrawler`, `ArticlesExtractor`. | Implemented | Must | P0 |
| FR-ART-002 | Requests shall be paced (`request_delay_s`, 1 req/s) and sent with an identifying User-Agent that names the crawler and a contact URL. | `articles.yaml`, `custom_article_crawler.py`. The UA contains `DigitalTwinCrawler`. | Partial. Pacing is implemented. The UA is a copy of a desktop Chrome string (`Mozilla/5.0 … Chrome/141.0.0.0 Safari/537.36`), which is not identifying and reads as browser impersonation. | Must | P1 |
| FR-ART-003 | The crawler shall check `robots.txt` before fetching and refuse disallowed URLs, recording `skipped: robots.txt`. | A URL disallowed for the crawler's UA is not fetched. | Planned | Must | P1 |
| FR-ART-004 | Article authors shall be extracted from page metadata where present. The site host is the fallback. | `author` equals the byline for pages with `<meta name="author">`. | Partial. Host only. | Could | P2 |
| FR-ART-005 | An article declared `origin: self` (the user's own blog post) shall get the declaring user's `owner_id`, with an owner-scoped source key so it cannot be claimed by another user. | `article` with `origin: self` yields a document with `owner_id=<user>` and passes DQ-4. Resolves OQ-08. | Planned. `ArticleSpec.owned` is fixed to `False`, so self articles have no owner and would be retrievable by every user as shared content. | Should | P1 |

### 2.5 Raw storage (STO)

| ID | Requirement | Acceptance criteria | Status | Priority | Phase |
|---|---|---|---|---|---|
| FR-STO-001 | Raw documents shall be stored behind an abstract `RawDataStore`, with the backend chosen by configuration (`RAW_STORE_BACKEND`). | `raw_data/store/{base,factory,mongo_store}.py`. | Implemented | Must | P0 |
| FR-STO-002 | Upserts shall be idempotent by `_id`. Scalar fields are replaced. `topics` and `source_ids` are merged with `$addToSet` (topic replacement rules: FR-ETL-013). Provenance is appended and capped at 50. | Re-running the same crawl changes no document count. `matched` grows and `inserted` is 0. | Implemented | Must | P0 |
| FR-STO-003 | Indexes shall exist on `provider`, `owner_id`, `source_ids`, `topics` and `origin`. | `MongoRawDataStore.setup`. | Implemented | Must | P0 |
| FR-STO-004 | Reading back a malformed record shall raise `StoreCorruptedError` with its location. | `_to_document`. | Implemented | Must | P0 |
| FR-STO-005 | Content changes shall be detectable. When `content_hash` differs from the stored value, the document shall be flagged changed (`changed_at`, previous hash kept), and the upsert result shall count `changed` separately from `unchanged`. | After an upstream edit, the next run reports `changed=1`, and the next feature run re-embeds only that document. | Planned. `UpsertStats` has only `inserted` and `matched`. | Must | P1 |
| FR-STO-006 | The store shall support tombstoning (`deleted_at`), un-tombstoning on reappearance, and hard purge by id, by source and by `owner_id`. | `RawDataStore` gains `tombstone`, `purge(owner_id=…)` and `purge(source_id=…)`. A purge by owner leaves 0 documents with that `owner_id`. Tombstoned documents are excluded from `find()` unless requested. | Planned. The store has no delete operation at all. Precondition for FR-ETL-010, FR-PRV-002, FR-PRV-003. | Must | P1 |
| FR-STO-007 | Stored records shall carry a `schema_version`. A change to `RawDocument` or `Source` that is not backward compatible shall ship with a migration command. | Every document has `schema_version`. Reading a record with an unknown higher version raises `StoreCorruptedError`. | Planned | Should | P1 |

### 2.6 Orchestration and CLI (ORC)

| ID | Requirement | Acceptance criteria | Status | Priority | Phase |
|---|---|---|---|---|---|
| FR-ORC-001 | The ETL shall run as a ZenML pipeline `digital_data_etl(user_id, source_ids)`: sync_registry → select_sources → crawl_{medium,github,linkedin,obsidian,articles} → version_raw_data → summarize. Caching is disabled. | `pipelines/digital_data_etl.py`. | Implemented | Must | P0 |
| FR-ORC-002 | A CLI shall start the ETL for all sources, one user, or explicit source ids, with a timestamped run name. | `uv run python -m tools.run --etl [--user U] [--source ID ...]`. | Implemented | Must | P0 |
| FR-ORC-003 | Each provider step shall return a summary: status `ok`/`partial`/`failed`/`skipped`, source and item counts, inserted and matched counts, stored total, and per-topic counts against the cap. | `crawl_provider` summary dict. | Implemented | Must | P0 |
| FR-ORC-004 | The run shall fail (`PipelineError`) after all steps finish if any provider status is `failed` or versioning failed. `partial` is a warning. Crawled data is kept in every case. | `summarize_crawl`. With FR-ETL-012, "all steps finish" also holds when an extractor has a bug. | Partial. Holds for `SourceError`s. Any other exception in a crawl step fails that step, and the remaining steps do not run. Data already flushed is kept. | Must | P1 |
| FR-ORC-005 | Later stages (feature, dataset, training, evaluation, deployment) shall each be a separate ZenML pipeline with typed artifacts. Each shall take the upstream data or model version as an explicit input. | Each pipeline run's metadata records the input version ids (raw `data_md5`, change-set id, dataset version, model version). | Planned | Must | P2 |
| FR-ORC-006 | Two runs that would crawl the same source shall not run concurrently. The second run shall wait or skip that source. Two runs shall not write snapshots or snapshot commits at the same time. | A lock per source (and per browser profile, and one for `version_raw_data`) is held during the crawl, with a lease that expires if the holder dies. A concurrent run reports `skipped: locked`. | Planned | Must | P1 |
| FR-ORC-007 | Each ETL run shall write a run record: run id, trigger kind, selection, code commit, a hash of `configs/`, per-provider summaries, change-set id, `data_md5` and git commit of the snapshot. | A `runs` collection (or a ZenML artifact) has one record per run, and the record is enough to find the snapshot and code that the run produced and used. | Planned. The summaries and versioning info exist as ZenML step metadata only; code and config hashes are not recorded. | Should | P1 |
| FR-ORC-008 | Each ETL run shall publish a change set: the ids of documents inserted, changed (FR-STO-005) and tombstoned (FR-ETL-010). This is the only input contract between the ETL and the feature pipeline. | The change-set artifact of a run with one edited note lists exactly that id under `changed`. The feature pipeline accepts a change-set id as input. | Planned | Must | P2 |

### 2.7 Data versioning (VER)

| ID | Requirement | Acceptance criteria | Status | Priority | Phase |
|---|---|---|---|---|---|
| FR-VER-001 | After each ETL run, the system shall export a deterministic snapshot: one JSONL per provider and one per registry collection, sorted by id with sorted keys, each file written atomically. Provenance and source state are excluded so diffs stay meaningful. | `RawDataSnapshotExporter`. Two exports of the same store are byte-identical. Known gap, accepted: the set of files is not replaced atomically as a whole, and list fields (`topics`, `source_ids`) keep insertion order. | Implemented | Must | P0 |
| FR-VER-002 | The snapshot shall be `dvc add`-ed. The pointer and DVC setup files shall be git-committed (`data: raw snapshot <run_id>`) and pushed to the configured DVC remote. Each action can be switched off by setting. | `version_raw_data` step. `DVC_ENABLED`, `DVC_AUTO_COMMIT`, `DVC_AUTO_PUSH`. Commits `264cc1c`, `d644b8b`, `088c488`. | Implemented | Must | P0 |
| FR-VER-003 | A versioning failure shall be reported but shall not roll back or corrupt stored data. | `status: failed` in the summary. The store is untouched. | Implemented | Must | P0 |
| FR-VER-004 | Every downstream artifact (cleaned docs, chunks, embeddings collection, instruction and preference datasets, adapters, eval reports) shall record the raw snapshot hash (`data_md5`) and git commit it came from. | Given a model version, `dvc checkout` of the recorded hash plus FR-VER-007 reproduces its training input. | Planned | Must | P2 |
| FR-VER-005 | Datasets for training shall be versioned and published as immutable named versions (private Hugging Face Hub repo or a DVC remote). | `dataset@vN` cannot be overwritten. Every new build gets a new version. | Planned | Must | P3 |
| FR-VER-006 | A snapshot commit shall reference only data that is already in the DVC remote, and shall not land on whatever branch the developer has checked out. | Order is `dvc add` → `dvc push` → `git commit`. A failed push produces no commit. Snapshot commits go to a dedicated `data` branch (or are tagged `data/<run_id>`) and never mix with unrelated staged changes. | Planned. Today the commit happens before the push (a failed push leaves a commit whose data a fresh clone cannot fetch), and commits land on the current branch (they are interleaved with code commits on `main`). | Should | P1 |
| FR-VER-007 | The system shall restore the raw store and registry from a snapshot. | `tools/restore_snapshot.py --rev <git rev>` loads the JSONL files into an empty database. A restore followed by an export yields byte-identical files. | Planned. Snapshots are write-only today, so "reproduce from `data_md5`" is not yet possible. | Should | P1 |
| FR-VER-008 | Snapshots shall be partitioned so that one user's own data can be removed without rewriting other users' data: shared external content in one partition, each user's `self` content in its own partition. | `data/raw/<provider>.jsonl` becomes `data/raw/shared/…` and `data/raw/users/<id>/…`. Deleting one user changes only their partition. | Planned (see OQ-06, RISK-12) | Should | P4 |

### 2.8 Triggers and scheduling (TRG)

| ID | Requirement | Acceptance criteria | Status | Priority | Phase |
|---|---|---|---|---|---|
| FR-TRG-001 | *Withdrawn: duplicate of FR-REG-007 (selection by explicit source ids, which is the trigger entry point).* | — | Withdrawn | — | — |
| FR-TRG-002 | A scheduler shall run the ETL on a configurable cadence for each provider (for example GitHub daily, Medium tags weekly), in unattended mode (FR-MED-008). | The schedule is defined in config. Runs appear in ZenML with `trigger=schedule`. | Planned | Must | P1 |
| FR-TRG-003 | Event triggers shall start ingestion of only the affected source when the user publishes new content. P1 mechanisms are polling and local: GitHub `pushed_at` polling, Medium author-feed polling (new GUID), Obsidian file watcher (debounced). Webhooks and the LinkedIn upload are P4 (FR-TRG-007, FR-LI-004). | A new commit to a tracked repo leads to an ETL run for `github:user:<u>` within one polling interval (default 15 minutes). | Planned | Should | P1 |
| FR-TRG-004 | Triggers shall be debounced and coalesced. Several events for the same source inside a window shall cause one run. | 10 vault saves within 5 minutes cause 1 run. | Planned | Should | P1 |
| FR-TRG-005 | A successful ETL run whose change set (FR-ORC-008) is not empty shall be able to trigger the feature pipeline for those document ids only. | A change set with `inserted+changed+tombstoned > 0` causes a feature run scoped to those ids. An empty change set causes no feature run. | Planned (depends on FR-STO-005, FR-ORC-008) | Must | P2 |
| FR-TRG-006 | Triggers shall respect provider backoff. A provider that ended with `RateLimitError(retry_after)` or `AccessBlockedError` shall not be retried before `retry_not_before` (FR-REG-014), or before a cool-down (default 24 h) for blocked access. | No run for that provider starts during the cool-down. The scheduler log shows `deferred`. | Planned (depends on FR-REG-014) | Must | P1 |
| FR-TRG-007 | Webhook endpoints, when built, shall verify signatures (for example the GitHub `X-Hub-Signature-256` HMAC) and reject unsigned or replayed requests. | An invalid signature returns 401 and no run starts. A replayed delivery id is ignored. | Planned. Needs a reachable endpoint, so it is not compatible with local-first until P4. | Must (if webhooks are built) | P4 |
| FR-TRG-008 | Every trigger event shall be logged (`TriggerEvent`) with its outcome, and a run that a trigger started and that failed shall be retried with bounded backoff, at most `max_attempts` (default 3), after which it is reported (FR-OPS-006). | The `trigger_events` collection shows each event, the run it was coalesced into, and the final status. | Planned | Should | P1 |

### 2.9 Source registration UI and API (UI)

| ID | Requirement | Acceptance criteria | Status | Priority | Phase |
|---|---|---|---|---|---|
| FR-UI-001 | An authenticated user shall be able to add a source through a form backed by the same Pydantic spec models used by YAML. | Invalid input shows the field-level validation message from the spec model. A valid one creates or reuses the canonical source and a subscription. | Planned (the spec models were designed for this: "YAML today, a UI form later") | Must | P4 |
| FR-UI-002 | When a user adds a source that already exists (same canonical key), the UI shall subscribe them to it and shall not create or crawl a duplicate. | The UI shows "already tracked, last crawled <ts>". No new source record is created. Merge rules: FR-REG-013. | Planned | Must | P4 |
| FR-UI-003 | The UI shall list the user's subscriptions with crawl state (status, last crawl, last success, error, item counts) read from the registry. | Values match `sources.state` for that source (FR-REG-006, FR-REG-014). | Planned | Must | P4 |
| FR-UI-004 | The UI shall let a user trigger an on-demand crawl of their own sources, rate-limited per user (default 1 run per source per hour). | The button is disabled during the cool-down. The API returns 429 when the limit is exceeded. | Planned | Should | P4 |
| FR-UI-005 | The UI shall support connecting own-content sources: GitHub (OAuth, read-only scope), LinkedIn export upload, and Obsidian vault upload or sync (zip or a git remote). | Credentials are stored encrypted (NFR-SEC-004). Revoking them removes them and disables dependent sources. | Planned | Should | P4 |
| FR-UI-006 | The UI shall let a user mark sources or documents as excluded from training and/or retrieval, and see what the twin was trained on. | An excluded document is absent from the next dataset build and from retrieval within 1 hour (its vectors are deleted or filtered). | Planned | Must | P4 |
| FR-UI-007 | An admin view shall manage users, topics, provider settings, and globally disabled sources. | Only users with role `admin` can reach it (HTTP 403 otherwise). | Planned | Should | P4 |
| FR-UI-008 | All UI operations shall be available through a versioned REST API (`/api/v1/...`) with an OpenAPI schema. | The OpenAPI document is served. The UI uses only the public API. | Planned | Must | P4 |
| FR-UI-009 | Users shall be authenticated. Registration shall be invite-only (NG3). The system shall support login and logout, session expiry, roles (`user`, `admin`), and account disable. | Without a valid session or token every `/api/v1` route except login returns 401. An invite link works once and expires after 7 days. A disabled account cannot log in, and its tokens stop working within 5 minutes. Mechanism (OIDC or passwordless email) is a P4 design decision. | Planned (missing from the draft, which assumed "an authenticated user" without a requirement for it) | Must | P4 |
| FR-UI-010 | Registration shall record the user's consent to processing of their data (terms version and timestamp) before any of their sources is crawled. | A user with no `Consent` record has no source selected by any run. Changing the terms version requires re-consent. Implements NFR-CMP-006. | Planned | Must | P4 |
| FR-UI-011 | A user shall prove they control an own-content account before it is registered as theirs (`owned` source). | A GitHub source becomes owned only after OAuth confirms the login equals `username`. LinkedIn and Obsidian are owned by upload, so control is implied. A failed proof leaves the declaration rejected (FR-REG-012). | Planned | Must | P4 |
| FR-UI-012 | Per-user quotas shall bound what one user can cost: maximum sources, maximum stored documents, on-demand crawls per day, and inference spend per day (FR-INF-008). | Exceeding a quota returns 429 or a validation error naming the quota. Quotas are set by the admin. | Planned | Should | P4 |

### 2.10 Feature pipeline (FEA)

| ID | Requirement | Acceptance criteria | Status | Priority | Phase |
|---|---|---|---|---|---|
| FR-FEA-001 | A feature pipeline shall read raw documents (all, by user, by provider, or by change set) and produce cleaned documents. Cleaning rules are per source kind and versioned: boilerplate and non-content markup removed, whitespace and unicode (NFC) normalised, tracking links and image references dropped, code blocks kept byte-for-byte. | A cleaned document stores `raw_id`, `content_hash_raw`, and `cleaner_version`. Golden-file tests (at least 3 inputs per source kind) pass. | Planned | Must | P2 |
| FR-FEA-002 | Chunking shall depend on the source kind: markdown or notes split by headings and token window; code split by function or class; posts and comments kept whole when below the window. Chunk size and overlap are configurable. | Defaults are recorded in config. No chunk exceeds the embedding model's max tokens. Every chunk carries `document_id`, `owner_id`, `origin`, `topics`, source kind, `url`, `position`. | Planned | Must | P2 |
| FR-FEA-003 | Chunks shall be embedded with a configurable embedding model, recorded by name, version and dimension. | Changing the model creates a new vector collection, so dimensions and models are never mixed. | Planned | Must | P2 |
| FR-FEA-004 | Embeddings and metadata shall be stored in a vector database (candidate: Qdrant) with payload filters on `owner_id`, `origin`, `topics`, `kind`, `deleted`. | A filtered search with `owner_id=X` returns only X's self chunks plus shared external chunks. | Planned | Must | P2 |
| FR-FEA-005 | The feature pipeline shall be incremental and idempotent. Re-running on unchanged data writes nothing. Changed documents replace their chunks (old chunk ids that no longer exist are deleted). Tombstoned or excluded documents have their vectors deleted. | Point ids are deterministic (hash of `document_id`, `chunk_index` and `cleaner_version`). A second run makes 0 upserts. After a tombstone, a search returns no chunk of that document. | Planned | Must | P2 |
| FR-FEA-006 | Cleaned documents and chunks shall be stored (or snapshotted) so that dataset generation does not re-clean. | A `cleaned_documents` collection (decision in OQ-04) contains the full cleaned text and is versioned per FR-VER-004. | Planned | Should | P2 |
| FR-FEA-007 | The pipeline shall drop or quarantine low-quality content: empty after cleaning, below a minimum length, mostly non-language (alphabetic ratio below 0.3 by default, or a base64 or minified run over 1,000 chars), or an exact duplicate by `content_hash`. | The quarantine count appears in the run summary with reasons, and quarantined ids can be listed. | Planned | Should | P2 |
| FR-FEA-008 | Secrets (API keys, tokens, private keys, passwords in URLs) shall be detected and masked before content enters the vector index. PII (emails, phone numbers, postal addresses) shall be masked before content enters training datasets (FR-DS-001). | A seeded test document with a fake API key and phone number comes out masked. A secret scanner finds 0 hits in the vector payloads and in the datasets. | Planned | Must | P2 (secrets), P3 (PII) |
| FR-FEA-009 | Embedding cost and throughput shall be bounded: a local embedding model is the default; a hosted model needs an estimated cost before the run and a cap (`max_usd`). | A full re-embed reports the token count and estimated cost before it starts, and aborts when the estimate exceeds the cap. | Planned | Should | P2 |
| FR-FEA-010 | Re-indexing (new embedding model or chunker) shall build a new collection and switch an alias when it is complete, so retrieval never reads a half-built index. | During a re-index, queries keep using the old collection. The alias switches in one operation, and the old collection is kept until the switch is confirmed. | Planned | Could | P2 |

### 2.11 Dataset generation (DS)

| ID | Requirement | Acceptance criteria | Status | Priority | Phase |
|---|---|---|---|---|---|
| FR-DS-001 | The system shall generate an instruction dataset (instruction → answer) from the user's cleaned content, using an LLM to write instructions for content chunks. Only style-eligible `self` content (FR-DS-008) teaches style. `external` content may be used only for knowledge-type samples, and only if FR-DS-006 allows it. | Each sample stores `owner_id`, `source_document_ids`, `origin`, `generator_model`, `prompt_version`, and the cleaned-data version it was built from. | Planned | Must | P3 |
| FR-DS-002 | The system shall generate a preference dataset (prompt, chosen, rejected) for DPO. `chosen` reflects the user's voice (derived from their own text). `rejected` is a generic or off-style answer. | Each sample has a non-identical chosen/rejected pair. Their origin is recorded. | Planned | Should | P3 |
| FR-DS-003 | Generated samples shall be filtered: deduplicated (exact and near), length-bounded (configurable min and max tokens), and checked by rules and/or an LLM judge for faithfulness to the source chunk. | A filter report lists counts removed per rule. The removal rate is reported. | Planned | Must | P3 |
| FR-DS-004 | Datasets shall be split train/test by source document, never by sample, so no document appears in both. | A leakage check finds 0 shared `document_id`s across splits, and 0 near-duplicate pairs across splits (FR-ETL-011 groups are assigned to one split). | Planned | Must | P3 |
| FR-DS-005 | Each dataset version (FR-VER-005) shall have a generated dataset card: sources, counts per topic and kind, generator model, filters, and licence notes. | The card is generated automatically with each version. | Planned | Should | P3 |
| FR-DS-006 | Third-party (`external`) content shall enter training datasets only if its licence permits. Otherwise it is limited to RAG retrieval. The default is retrieval only. | The dataset build excludes `external` documents unless `license_allows_training=true` is recorded for the source. | Planned (see OQ-03) | Must | P3 |
| FR-DS-007 | The cost of LLM calls for generation shall be estimated before a run and capped by configuration. | A run aborts when the estimated cost exceeds `max_usd`. Actual cost is logged and counted against NFR-COST-001. | Planned | Must | P3 |
| FR-DS-008 | Each `self` document shall have a style-eligibility decision, from configurable rules per source and path (for example notes under `myLibrary/Books/*` that are mostly quotations or course transcripts are knowledge, not style), plus a quotation-ratio heuristic. | The dataset build uses only style-eligible documents for style samples. The build report lists eligible and ineligible counts per source and folder, and the owner can override per path. | Planned | Must | P3 |
| FR-DS-009 | A human-curated evaluation set shall be kept apart from generated data: prompts with reference answers written or approved by the owner, covering style and knowledge per topic. | At least 50 owner-approved items before the first promotion. The set is versioned, never used for training, and checked for overlap with training data. | Planned | Must | P3 |
| FR-DS-010 | Training shall not start on a dataset below minimum size and quality thresholds. | The training pipeline refuses a dataset with fewer than `min_samples` (default 1,000 instruction samples) or a filter removal rate above `max_removal_rate` (default 50%). | Planned | Should | P3 |

### 2.12 Fine-tuning (FT)

| ID | Requirement | Acceptance criteria | Status | Priority | Phase |
|---|---|---|---|---|---|
| FR-FT-001 | The system shall fine-tune an open-weight base model (candidate: an 8B-class model, with LoRA or QLoRA) with SFT on the instruction dataset. | The training run logs the base model and revision, dataset version, hyperparameters, seed, and loss curves. The adapter is saved. | Planned (blocked by OQ-02) | Must | P3 |
| FR-FT-002 | The system shall then run preference alignment (DPO) on the preference dataset, starting from the SFT checkpoint. | The DPO run references the parent SFT model version. | Planned | Should | P3 |
| FR-FT-003 | Training shall be reproducible from recorded inputs: base model revision, dataset version, config, seed, library versions and hardware class. | A re-run from the recorded config on the same hardware class lands within ±2 points (absolute) of the reference on each gating metric of FR-EVAL-001. | Planned | Should | P3 |
| FR-FT-004 | Trained models and adapters shall be registered with metadata and lineage (data snapshot, dataset version, parent model, eval report). They shall be stored privately. | Registry entries are immutable. Promotion uses tags (`staging`, `production`). | Planned | Must | P3 |
| FR-FT-005 | One adapter shall be trained per user. A user's adapter shall never be trained on another user's `self` data. | The dataset filter is checked in the pipeline (FR-REG-010), and the training step asserts that every sample's `owner_id` equals the target user or is null (external). | Planned | Must | P4 |
| FR-FT-006 | Training shall run on configurable compute (local GPU or a cloud GPU job), with a cost and time budget. | The job is cancelled when it exceeds `max_hours` or `max_usd`. | Planned | Must | P3 |

### 2.13 Evaluation (EVAL)

| ID | Requirement | Acceptance criteria | Status | Priority | Phase |
|---|---|---|---|---|---|
| FR-EVAL-001 | Each candidate model shall be evaluated on the held-out split and on the curated set (FR-DS-009) for: style similarity to the user (LLM judge and/or a stylometric classifier), answer relevance, and factual faithfulness. | The eval report stores per-metric scores with 95% confidence intervals and the judge model and prompt version. | Planned | Must | P3 |
| FR-EVAL-002 | General-capability regression shall be measured on at least one public benchmark subset, to detect catastrophic forgetting. | A drop greater than a configured threshold (default 5 points) blocks promotion. | Planned | Should | P3 |
| FR-EVAL-003 | The RAG system shall be evaluated on a curated question set: retrieval (recall@k, MRR) and generation (faithfulness, answer relevance, context precision). | A test set with reference sources: at least 50 questions in P2, at least 100 by the end of P3. Metrics are reported per topic. | Planned | Must | P2 |
| FR-EVAL-004 | Promotion to `production` shall require passing configured thresholds against the current production model. | In P3 the training pipeline's promote step enforces the gate. From P4 it is also enforced in CD (FR-OPS-004). | Planned | Must | P3 |
| FR-EVAL-005 | Safety checks shall verify that the twin refuses or deflects requests to reveal private data or secrets, resists prompt injection placed in retrieved content (NFR-SEC-006), and discloses it is an AI when asked. | A red-team prompt set reaches a pass rate of at least 95% (configurable). | Planned | Must | P3 |

### 2.14 RAG inference service (INF)

| ID | Requirement | Acceptance criteria | Status | Priority | Phase |
|---|---|---|---|---|---|
| FR-INF-001 | The system shall expose an HTTP API (for example `POST /api/v1/twins/{user_id}/chat`) that takes a query and optional conversation history and returns an answer with cited sources. | The response contains `answer`, `sources[]` (document id, title, url, origin), `model_version`, `trace_id`, `ai_disclosure`. | Planned | Must | P2 |
| FR-INF-002 | Retrieval shall support query expansion or rewriting, self-query metadata extraction (topic, kind), filtered vector search scoped to the user, and reranking. | Retrieval returns only chunks with `owner_id ∈ {user, null}` and not deleted. The reranker cuts to top-k (configurable). Each technique can be switched off, and FR-EVAL-003 reports its effect. | Planned | Should | P2 |
| FR-INF-003 | Generation shall use the user's fine-tuned model, falling back to the base model plus a style prompt if it is unavailable. The model version shall be reported. | When the adapter fails to load, the fallback answer carries `model_version=fallback`. In P2, before any adapter exists, the base model plus style prompt is the normal path. | Planned | Must | P3 |
| FR-INF-004 | The service shall support streaming responses. | First token arrives within the NFR-PERF-004 budget. | Planned | Could | P2 |
| FR-INF-005 | Requests shall be authenticated, and a user shall reach only their own twin unless that twin is explicitly shared publicly (OQ-10). | P2: a static bearer token is required on every non-health route. P4: per-user auth (FR-UI-009); a request with another user's id returns 403. | Planned | Must | P2 (token), P4 (per user) |
| FR-INF-006 | Every answer shall carry an AI-generated disclosure for twin consumers. | The disclosure field or banner is present in the API and UI. | Planned | Must | P2 |
| FR-INF-007 | When retrieval finds nothing relevant (all scores below a configured threshold), the twin shall say it does not know instead of answering from the model alone on knowledge questions. Citations shall only name retrieved chunks. | On an off-corpus question set, at least 90% of answers are "don't know" responses. No response cites a document that was not retrieved for it. | Planned | Must | P2 |
| FR-INF-008 | Inference shall be rate-limited and cost-capped: per user requests per minute, and a daily spend cap for any paid model or GPU endpoint, with a global cap from NFR-COST-001. | Over the rate limit returns 429. Over the daily cap returns 503 with a `budget_exhausted` reason until the next period. | Planned | Must | P2 |

### 2.15 LLMOps: monitoring, CI/CD, deployment (OPS)

| ID | Requirement | Acceptance criteria | Status | Priority | Phase |
|---|---|---|---|---|---|
| FR-OPS-001 | Every inference request shall be traced: prompt template version, retrieved chunk ids, model version, latency per stage, token counts, cost (candidate: Opik, already a declared dependency). | A trace is viewable by `trace_id`. 100% of requests are traced by default (sampling is configurable). | Planned (`opik` is in `pyproject.toml` but not imported anywhere) | Should | P2 |
| FR-OPS-002 | Prompt templates shall be versioned and referenced by version in traces. | Changing a template bumps its version. Traces show the version used. | Planned | Should | P2 |
| FR-OPS-003 | CI shall run on every push: lint (ruff), type check (mypy), unit and contract tests, config validation (`validate_sources --offline`) and a secret scan. | The CI workflow exists. Merging to `main` is blocked on failure. | Planned (no `.github/`, no tests, no ruff or mypy configuration in `pyproject.toml`) | Must | P1 |
| FR-OPS-004 | CD shall build and deploy the inference service as a container. The model is promoted through `staging` → `production` with eval gating (FR-EVAL-004) and one-step rollback. | Rollback to the previous model version takes ≤ 5 minutes. | Planned | Should | P4 |
| FR-OPS-005 | Online monitoring shall alert on: error rate, p95 latency, cost per day, retrieval empty-result rate, and (sampled) LLM-judge quality drift. | Alert thresholds are configured. A test alert fires. | Planned | Should | P4 |
| FR-OPS-006 | Pipeline monitoring shall alert when an ETL provider ends `failed`, or the same source fails on N consecutive runs (default 3). | An alert names the source and the last error from `sources.state` (`consecutive_failures`, FR-REG-014). | Planned | Should | P1 |
| FR-OPS-007 | User feedback (thumbs up/down, corrections) on answers shall be captured and linked to the trace, for later preference data. | Feedback is stored with `trace_id`. It can be exported into a DPO candidate set. | Planned | Could | P4 |
| FR-OPS-008 | All spend (LLM APIs, embedding APIs, GPU jobs, hosting) shall be metered against the budgets of NFR-COST-001, with a hard stop when a budget is exhausted. | A cost ledger records every paid call or job with amount and stage. When the monthly budget is reached, new paid jobs are refused and an alert fires. | Planned | Must | P2 |
| FR-OPS-009 | MongoDB (registry, raw and cleaned documents, traces) and the vector DB shall be backed up on a schedule, and restore shall be tested. | A restore drill from the last backup (and, for raw data, from a DVC snapshot via FR-VER-007) completes within NFR-REL-007. | Planned | Should | P1 |

### 2.16 Privacy and data-subject operations (PRV)

| ID | Requirement | Acceptance criteria | Status | Priority | Phase |
|---|---|---|---|---|---|
| FR-PRV-001 | A user shall be able to export all data held about them: registry records, own documents, datasets and model lineage. | The export contains every document with `owner_id=user`. | Planned | Should | P4 |
| FR-PRV-002 | A user shall be able to delete their account. This removes their user record, subscriptions, own documents, cleaned documents, chunks and vectors, own datasets and adapters, and their traces. It shall also cover future DVC snapshots (FR-VER-008) and document how past snapshots are handled (OQ-06). | Within 7 days of the request, queries for `owner_id=user` return 0 across Mongo and the vector DB. A deletion log entry exists. Models trained on the data follow FR-PRV-005. | Planned | Must | P4 |
| FR-PRV-003 | When a shared external source loses its last subscriber, its documents shall be retained or purged by a configurable policy. | The policy is applied at sync (FR-REG-008), and the result is reported. | Planned | Should | P1 |
| FR-PRV-004 | Personal data of third parties found in own content (names, emails or phone numbers of others in comments, notes or diaries) shall be minimised before training: replaced with typed placeholders by an NER pass in addition to the pattern masking of FR-FEA-008. | On a seeded test set of notes containing other people's names, recall of the replacement is at least 90%. | Planned | Must | P3 |
| FR-PRV-005 | A model or adapter trained on data that was later deleted or excluded shall be flagged, and retrained without that data or retired within a defined window. | Deleting a document used by the production adapter marks that adapter `tainted`. A tainted adapter is retrained or retired within 30 days (configurable), and the action is logged. | Planned | Must | P4 |
| FR-PRV-006 | The owner shall be able to "forget" a document or a path pattern with one command, which tombstones it, excludes it from future crawls, and removes it from the vector index and future datasets. | `tools/forget.py --doc <id>` or `--glob <pattern>` leaves no retrievable chunk, and the next dataset build excludes it. | Planned | Should | P2 |

---

## 3. Non-functional requirements

Each NFR has a measure, a status at the baseline, and the phase from which it applies.

### 3.1 Performance (PERF)
| ID | Requirement | Measure | Status | Phase |
|---|---|---|---|---|
| NFR-PERF-001 | A full ETL of the owner's current sources shall complete in one unattended run. | ≤ 3 h wall-clock for about 2.6k documents with default pacing, measured from ZenML run duration. | Not measured | P1 |
| NFR-PERF-002 | A single-source triggered ETL (one GitHub account, one author feed) shall complete quickly. | ≤ 10 min (GitHub with change detection) and ≤ 2 min (one feed). | Planned | P1 |
| NFR-PERF-003 | The feature pipeline shall handle incremental updates efficiently. | ≤ 5 min for ≤ 100 changed documents on the owner's workstation with a local embedding model (hardware recorded with the measurement). | Planned | P2 |
| NFR-PERF-004 | RAG API latency (non-streaming, excluding cold start). | p95 ≤ 5 s end-to-end. Time to first token (streaming) p95 ≤ 1.5 s. Retrieval stage p95 ≤ 300 ms. | Planned | P2 |
| NFR-PERF-005 | Vector search shall scale to the expected corpus size. | ≥ 100k chunks with p95 search ≤ 100 ms. | Planned | P2 |

### 3.2 Reliability and idempotency (REL)
| ID | Requirement | Measure | Status | Phase |
|---|---|---|---|---|
| NFR-REL-001 | Every pipeline shall be idempotent. Re-running with the same inputs and unchanged upstream data produces no new records and no duplicate vectors. | ETL: stable ids, upserts, `$addToSet`. Downstream: FR-FEA-005. | ETL: Implemented. Downstream: Planned. | P0 / P2 |
| NFR-REL-002 | A failure in one source or provider shall not prevent the others from running, and shall not lose their data. | Error levels, batch flush in `finally`, `summarize` raises only at the end. Fault-injection test of FR-ETL-012. | Partial. Holds for `SourceError`s. An unexpected exception in one crawl step stops the remaining steps (FR-ETL-012). | P1 |
| NFR-REL-003 | *Withdrawn: duplicate of FR-ETL-009.* | — | Withdrawn | — |
| NFR-REL-004 | Snapshot writes shall be atomic per file. | `.tmp` plus `os.replace`. | Implemented | P0 |
| NFR-REL-005 | External calls shall use timeouts and bounded retries with backoff. No unbounded waits. | Every HTTP client sets a timeout of at most 60 s. Every retry loop has a maximum. | Partial: Medium feeds (timeout 20 s, retries), GitHub (timeout 30 s, no automatic retry), browser (page-load and challenge timeouts), Mongo (`timeout_ms=5000`). Articles use the `AsyncHtmlLoader` default timeout with no retry. | P1 |
| NFR-REL-006 | The inference service shall reach 99% monthly availability once deployed (single-user scale). | Uptime checks. | Planned | P4 |
| NFR-REL-007 | Backups shall bound data loss and recovery time. | RPO ≤ 24 h for Mongo and the vector DB (raw documents: last DVC snapshot). RTO ≤ 2 h, proven by a restore drill each phase (FR-OPS-009). | Planned | P1 |

### 3.3 Scalability (SCL)
| ID | Requirement | Measure | Status | Phase |
|---|---|---|---|---|
| NFR-SCL-001 | The registry design shall support at least 50 users and 5k sources without schema change. Shared sources are crawled once regardless of subscriber count, and their declarations merge deterministically. | Crawl cost scales with unique sources, not subscriptions. FR-REG-012 and FR-REG-013 hold. | Partial. Dedup is implemented. Merge semantics are last-writer-wins (FR-REG-013), and the exporter and `topics_by_id` load whole collections into memory. | P1 |
| NFR-SCL-002 | Storage backends (raw store, registry, vector DB) shall be swappable behind interfaces. | Abstract base plus factory per backend. | Implemented for the raw store and registry. Planned for the vector DB. | P0 / P2 |
| NFR-SCL-003 | Provider steps shall be parallelisable across providers. | The steps are independent in the DAG. An orchestrator that runs steps in parallel completes a full ETL faster than the sum of the steps. | Planned (they currently run on the local orchestrator, one at a time) | Could, P4 |

### 3.4 Security (SEC)
| ID | Requirement | Measure | Status | Phase |
|---|---|---|---|---|
| NFR-SEC-001 | Secrets shall never be committed or logged. | `.env*` is git-ignored. `SecretStr`. `display_uri` masks the Mongo password. A CI secret scan (FR-OPS-003). | Implemented, except the CI scan (Planned). | P0 / P1 |
| NFR-SEC-002 | Any non-localhost deployment of MongoDB or the vector DB shall require authentication and TLS. | A deployment check refuses to start against a non-localhost store without credentials and TLS. | Planned. Current state: Mongo in Docker, no auth, localhost only (accepted for local-first). | P4 |
| NFR-SEC-003 | The UI and API shall use authenticated sessions or tokens, role-based access (user, admin), CSRF protection for forms, and per-user rate limits. | See FR-UI-009, FR-UI-012, FR-INF-005. | Planned | P4 |
| NFR-SEC-004 | Third-party credentials (GitHub tokens, OAuth) shall be stored encrypted at rest, scoped to read-only, and revocable. | Encryption key outside the database. Revocation tested. | Planned | P4 |
| NFR-SEC-005 | The crawler browser profile shall be dedicated to the crawler (never the everyday profile) and shall not be committed. | `user_data_dir: ~/.config/digital-twin-chrome`, outside the repo. Chrome 136+ refuses automation of the default profile, and `Browser._profile_hint` explains why. | Implemented (by configuration; the code does not itself refuse an everyday profile) | P0 |
| NFR-SEC-006 | Ingested content shall be treated as untrusted. Retrieved text shall not be able to change system instructions (prompt-injection defences in RAG). | Injection test cases in FR-EVAL-005. | Planned | P2 |
| NFR-SEC-007 | Dependencies shall be pinned (`uv.lock`) and scanned for known vulnerabilities in CI. | Lockfile present. Scan in FR-OPS-003. | Lockfile Implemented. Scan Planned. | P0 / P1 |

### 3.5 Privacy (PRIV)
| ID | Requirement | Measure | Status | Phase |
|---|---|---|---|---|
| NFR-PRIV-001 | Raw data, datasets and models containing personal content shall stay private: local or private remotes only, never in the public git repo. | Git holds only DVC pointers. | Implemented for raw data (DVC remote on a local drive). Datasets and models: Planned. | P0 / P3 |
| NFR-PRIV-002 | The public repository shall not expose personal paths or private identifiers beyond what the owner accepts. Local tool state shall not be committed. | No absolute home paths or employer names in tracked files. `.zen/` is git-ignored. | Partial. The absolute vault path was replaced by `~/Desktop/workDiaries` in `4c40ca7` (older commits still contain it). Still open: `obsidian.yaml` names an employer test, `.dvc/config` holds a local drive path, `.zen/` is untracked but not ignored. See OQ-07. | P1 |
| NFR-PRIV-003 | Data minimisation: only content needed for style or knowledge is ingested. Sensitive folders are excludable. | Glob excludes; frontmatter opt-out (FR-OBS-004). | Partial (glob excludes only) | P1 |
| NFR-PRIV-004 | Inference traces shall be retained for a bounded period (default 90 days) and then deleted or anonymised. | A scheduled job enforces it. | Planned | P2 |

### 3.6 Maintainability (MNT)
| ID | Requirement | Measure | Status | Phase |
|---|---|---|---|---|
| NFR-MNT-001 | Code organisation: one package per provider, pure helpers in `utils/`, settings in `settings/`, one exception hierarchy rooted at `DigitalTwinError`. Adding a source type means adding one spec module, one registry entry and the extractor handling. | Code review. | Implemented | P0 |
| NFR-MNT-002 | Automated tests: unit tests for pure functions (keys, globs, parsers, topic matcher, markdown cleaners); contract tests for each extractor with recorded fixtures (no network); store tests against an ephemeral Mongo. | ≥ 70% line coverage on `llm_engineering/` excluding infrastructure adapters. | Planned. There is no `tests/` directory. | P1 |
| NFR-MNT-003 | Static checks (ruff, mypy) shall pass with zero errors on `main`. | Enforced in CI. Ruff and mypy configured in `pyproject.toml` and listed as dev dependencies. | Planned (caches suggest local runs; nothing is configured or enforced) | P1 |
| NFR-MNT-004 | Documentation: the README covers setup, running, configuration and architecture. Each pipeline has a docstring describing its inputs and outputs. | README sections present. | Docstrings Implemented. `README.md` is empty (0 bytes), so Planned. | P1 |
| NFR-MNT-005 | Python 3.12+, dependency management with `uv`, ZenML pinned (`0.96.3`). | `pyproject.toml`, `uv.lock`. | Implemented | P0 |
| NFR-MNT-006 | Dependencies and project metadata shall be accurate: no declared dependency that is not imported, no placeholder metadata, no stub entry points. | A dependency checker in CI reports 0 unused dependencies. | Planned. `commit` and `fonttools` are declared but not imported by project code, `opik` is unused until FR-OPS-001, the `pyproject` description is the `uv init` placeholder, and `main.py` prints "Hello from digitaltwin!". | P1 |

### 3.7 Observability (OBSV)
| ID | Requirement | Measure | Status | Phase |
|---|---|---|---|---|
| NFR-OBSV-001 | Every pipeline run shall be identifiable (`run_id`) and traceable from a stored document back to the run that last saw it. | Run name, `provenance.run_id`, `sources.state.last_run_id`. | Implemented | P0 |
| NFR-OBSV-002 | Each ETL run shall show a per-provider, per-source, per-item report with outcome reasons. | HTML report artifact. | Implemented | P0 |
| NFR-OBSV-003 | Logs shall be structured: level, provider, source id, run id. | JSON log lines with those fields. | Partial (standard logging with provider and source in messages; not structured) | P1 |
| NFR-OBSV-004 | Metrics shall be exported over time: documents per provider and topic, failure rate per source, crawl duration, and (later) inference latency, cost and quality. | A time series per metric. | Planned | P1 (ETL) / P4 (inference) |

### 3.8 Compliance and ethics (CMP)
| ID | Requirement | Measure | Status | Phase |
|---|---|---|---|---|
| NFR-CMP-001 | Only official, terms-permitted channels shall be used for content: RSS feeds, official REST APIs, user-initiated data exports, local files, and public pages that do not forbid crawling. | Per provider review. | Implemented for Medium text (RSS), GitHub (API) and LinkedIn (export). Articles need robots.txt (FR-ART-003). See RISK-01 for Medium tag discovery. | P0 / P1 |
| NFR-CMP-002 | No paywall, login-wall, CAPTCHA or bot-detection circumvention. A bot challenge that does not clear on its own shall end browser use for the run (`AccessBlockedError` with RSS fallback, FR-MED-003). No person solves a challenge for the crawler, and no technique is used whose purpose is to look like a human to a bot detector. | Unattended mode never starts a browser (FR-MED-008). | Partial. Member-only content is skipped and blocked discovery falls back to RSS. But `medium.yaml` sets `headless: false`, the browser waits 30 s "so you can click the check", and it uses a logged-in profile with randomised human-like pauses and wheel scrolling. See RISK-01, OQ-01. | P1 |
| NFR-CMP-003 | Polite crawling: identifying User-Agent, minimum delays, backoff on 429 and 5xx, honouring `Retry-After`, and robots.txt for generic pages. | Per provider review. | Partial: delays and backoff are implemented. `Retry-After` is ignored by the Medium feed client. The article crawler sends a copied Chrome UA (FR-ART-002). robots.txt is Planned (FR-ART-003). The browser uses a stock UA. | P1 |
| NFR-CMP-004 | External content shall keep attribution (author, url) and shall not be redistributed. Raw external text shall not appear in any public artifact (repo, public dataset, public model card). | A CI check that public artifacts contain no `origin=external` text. | Attribution fields: Implemented. Non-redistribution checks: Planned. | P0 / P3 |
| NFR-CMP-005 | Model and dataset licences shall be compatible with the base model's licence and the project's proprietary licence. The licence of each training-data source shall be recorded. | Licence field per source and per dataset card. | Planned | P3 |
| NFR-CMP-006 | Data of users other than the owner shall be processed only with their explicit consent, recorded at registration (terms acceptance and timestamp). | FR-UI-010. | Planned | P4 |

### 3.9 Cost (COST)
| ID | Requirement | Measure | Status | Phase |
|---|---|---|---|---|
| NFR-COST-001 | Every paid resource shall have a monthly budget with a hard stop: LLM API (dataset generation, judging, inference), embedding API, GPU compute, hosting. | Budgets in config. Defaults to be set by the owner (OQ-13). FR-OPS-008 enforces them. | Planned | P2 |
| NFR-COST-002 | The cost of each pipeline run and each inference request shall be visible. | Cost per run in the run record (FR-ORC-007) and per request in the trace (FR-OPS-001). | Planned | P2 |

---

## 4. Constraints and assumptions

### 4.1 Constraints
- C1: **Local-first.** MongoDB runs in Docker on localhost. The DVC remote is a local drive (`/run/media/omar/My Passport1/dvc-remotes/DigitalTwin`). ZenML uses its local server.
- C2: **Stack decisions already made:** Python 3.12, uv, Pydantic v2 and pydantic-settings, MongoDB, ZenML 0.96.3, DVC, Selenium (Chromium) for Medium tag discovery only, LangChain loaders for articles and Obsidian.
- C3: **Proprietary licence** (`LICENSE`, classifier `Private :: Do Not Upload`), while the GitHub repository is public.
- C4: **Single operator with limited budget.** Every paid resource is capped (NFR-COST-001, FR-DS-007, FR-FT-006, FR-INF-008).
- C5: **Platform limits:** Medium feeds carry only about the latest 10 posts per feed. GitHub allows 60 req/h without a token and 5000 req/h with one. LinkedIn content comes only via a manual export, with platform-defined latency.
- C6: **Medium tag discovery through the browser needs a headed browser with a dedicated profile.** It cannot run unattended. Unattended runs use RSS only (FR-MED-008).
- C7: **The Obsidian vault is on the owner's machine.** Obsidian ingestion cannot run elsewhere without a sync mechanism.

### 4.2 Assumptions
- A1: The owner's GitHub repositories, Obsidian notes and LinkedIn posts are predominantly the owner's own writing. Known exception: course and book notes in the vault (`myLibrary/Courses/*`, `myLibrary/Books/*`) may be largely paraphrase or quotation; FR-DS-008 decides their style eligibility.
- A2: Free Medium posts delivered in full through official RSS may be read and stored privately for personal retrieval. See OQ-03 on training use.
- A3: About 100 external items per topic is enough knowledge coverage for RAG in the first iteration.
- A4: Future users are few (≤ 50) and known to the owner.
- A5: An open-weight base model of about 8B parameters fine-tuned with LoRA can capture style on the owner's hardware or affordable cloud GPUs.

---

## 5. Data requirements

### 5.1 Entities (current: Implemented)

**User** (`users`): `_id` (pattern `^[a-z0-9][a-z0-9_-]*$`, equal to the config folder name), `name` (author of own documents), `handles{platform→handle}`.

**Source** (`sources`): `_id` (canonical key, for example `medium:tag:rag`, `medium:author:@x`, `github:user:x`, `obsidian:<user>:<abs path>`, `linkedin:<user>`, `article:<normalised url>`), `type`, `provider`, `spec` (declared JSON), `owner_id?`, `topics[]`, `enabled`, `state{status, last_run_id, last_crawled_at, error, items_ok, items_failed, items_skipped}`. Planned additions: `state.{last_success_at, last_success_run_id, consecutive_failures, cursor, retry_not_before}` (FR-REG-014), `declared_via` (FR-CFG-008), `schema_version` (FR-STO-007).

**Subscription** (`subscriptions`): `user_id`, `source_id`, `created_at`. `_id` is `user|source`, with a unique index on the pair. Planned: per-subscriber `topics` (FR-REG-013), `declared_via`.

**RawDocument** (`raw_documents`): see FR-ETL-004. Ids: `medium:<article_id>`, `github:<owner/repo>/<path>`, `obsidian:<user>:<rel path>`, `article:<16-hex sha1 of the source id>`, `linkedin_post|linkedin_comment|linkedin_article:<user>:<short hash>`. `source` kind ∈ {medium, linkedin_post, linkedin_article, linkedin_comment, obsidian, github, article}. `origin` ∈ {self, external}. Planned additions: `deleted_at`, `changed_at`, `previous_content_hash`, `schema_version`, `metadata.sha` for GitHub.

**Provenance**: `source_id`, `query`, `rank?`, `run_id`, `collected_at`.

**Topic** (YAML): key, `description`, `medium_tags[]`, `obsidian_tags[]` (31 topics).

**Snapshot** (DVC): `data/raw/<provider>.jsonl` and `data/raw/registry/{users,sources,subscriptions}.jsonl`. Identified by `data_md5` and the git commit.

### 5.2 Entities (planned)
| Entity | Key fields | Introduced by |
|---|---|---|
| RunRecord | `run_id`, `trigger`, `selection`, `code_commit`, `config_hash`, `summaries`, `change_set_id`, `data_md5`, `snapshot_commit`, `cost` | FR-ORC-007 |
| ChangeSet | `id`, `run_id`, `inserted[]`, `changed[]`, `tombstoned[]` | FR-ORC-008 |
| CleanedDocument | `id` (= raw id), `owner_id`, `origin`, `kind`, `topics`, `content`, `raw_content_hash`, `cleaner_version`, `style_eligible`, `deleted_at?` | FR-FEA-001, FR-DS-008 |
| Chunk / vector point | `point_id` (hash of doc id, index and cleaner version), `document_id`, `chunk_index`, `text`, `embedding`, `embedding_model`, `owner_id`, `origin`, `topics`, `kind`, `url`, `title`, `deleted` | FR-FEA-002..005 |
| InstructionSample | `id`, `owner_id`, `instruction`, `answer`, `source_document_ids[]`, `origin`, `generator_model`, `prompt_version`, `split` | FR-DS-001 |
| PreferenceSample | `id`, `owner_id`, `prompt`, `chosen`, `rejected`, `source_document_ids[]`, `generator_model`, `split` | FR-DS-002 |
| DatasetVersion | `name`, `version`, `kind` (instruction/preference/eval), `raw_snapshot_md5`, `cleaned_version`, `counts`, `card` | FR-VER-005, FR-DS-005 |
| ModelVersion | `id`, `owner_id`, `base_model@rev`, `stage` (sft/dpo), `parent_id?`, `dataset_versions[]`, `hyperparams`, `eval_report_id`, `tags` (staging/production/tainted) | FR-FT-004, FR-PRV-005 |
| EvalReport | `model_id`, `suite`, `metrics{}`, `ci{}`, `thresholds{}`, `passed`, `judge_model` | FR-EVAL-001 |
| Trace | `trace_id`, `user_id`, `query`, `retrieved_chunk_ids[]`, `prompt_version`, `model_version`, `latency_ms{}`, `tokens`, `cost`, `feedback?` | FR-OPS-001 |
| TriggerEvent | `id`, `source_id`, `kind` (schedule/webhook/poll/watch/manual), `received_at`, `coalesced_into_run?`, `attempt`, `status` | FR-TRG-008 |
| Credential | `user_id`, `provider`, `encrypted_secret`, `scopes`, `created_at`, `revoked_at?` | FR-UI-005 |
| Consent | `user_id`, `terms_version`, `accepted_at` | FR-UI-010 |
| CostEntry | `id`, `stage`, `resource`, `amount_usd`, `user_id?`, `run_id?`, `trace_id?`, `at` (`user_id` makes per-user daily caps computable) | FR-OPS-008, FR-INF-008, FR-UI-012 |
| Exclusion | `id`, `user_id`, `target` (document id, source id or glob), `scopes` (crawl/retrieval/training), `created_at` | FR-UI-006, FR-PRV-006, FR-OBS-004 |
| Lock | `key` (source id, browser profile or `snapshot`), `owner_run_id`, `expires_at` (TTL lease) | FR-ORC-006 |
| SourceState (extended) | adds `last_success_at`, `last_success_run_id`, `consecutive_failures`, `cursor` (source-level watermark only; per-item fingerprints are read from `raw_documents`), `retry_not_before` | FR-REG-011, FR-REG-014 |
| RawDocument (extended) | adds `deleted_at?`, `changed_at?`, `previous_hash?`, `schema_version`, `topics_by_source{}` (lets FR-ETL-013 replace one source's derived topics) | FR-ETL-010, FR-ETL-013, FR-STO-005..007 |
| DeletionLog | `id`, `user_id?`, `scope`, `requested_at`, `completed_at`, `stores[]` | FR-PRV-002, FR-PRV-006 |

### 5.3 Data quality rules
- DQ-1: `content` is non-empty and at least the source's `min_chars` (enforced per provider today).
- DQ-2: `content_hash` = sha256(content) for every document (Implemented).
- DQ-3: Every `topics` entry is a key in `topics.yaml` (enforced at config load for declared topics; mapped topics come from `topics.yaml` by construction; stale keys after a rename are FR-CFG-007).
- DQ-4: `owner_id` is set if and only if `origin=self`. The baseline violates this for `article` with `origin=self` (no owner); fixed by FR-ART-005.
- DQ-5: An owned source has exactly one owner, and its `owner_id` never changes (FR-REG-012).
- DQ-6: A tombstoned document has no live vectors and is in no dataset built after the tombstone (FR-FEA-005, FR-DS-001).

### 5.4 Current volumes (baseline)
About 2,560 documents: GitHub 1190, Obsidian 1017, Medium 343, Articles 12, LinkedIn 0 (export pending). 31 topics. Medium cap 100 per topic.

---

## 6. External interfaces

| Interface | Direction | Protocol / format | Notes |
|---|---|---|---|
| Medium RSS (`medium.com/feed/@author`, `/feed/<publication>`, `/feed/tag/<tag>`) | In | HTTPS, RSS/XML | Official. Paced at 3 s, with retries. |
| Medium tag pages (`/tag/<t>/recommended`) | In | Browser (Selenium, Chromium) | Link discovery only, interactive mode only. Falls back to RSS when blocked. See RISK-01. |
| GitHub REST API v3 and `raw.githubusercontent.com` | In | HTTPS JSON, optional bearer token | Endpoints: user repos, git trees; file bodies from the raw host. |
| LinkedIn data export | In | Files (CSV, HTML) in `data/exports/linkedin/<user>` | Git-ignored. Downloaded manually. |
| Obsidian vault | In | Local filesystem (markdown, PDF) | |
| Arbitrary web pages | In | HTTPS HTML → markdown | No JavaScript. 1 req/s. robots.txt from P1. |
| MongoDB | In/Out | `mongodb://` or `mongodb+srv://` | Collections `users`, `sources`, `subscriptions`, `raw_documents`. Planned: `runs`, `change_sets`, `trigger_events`, `cleaned_documents`, `cost_ledger`. |
| DVC remote | Out | DVC (local path today) | |
| Git | Out | Local commits of snapshot pointers | Pushing to GitHub is not automated. Dedicated branch from P1 (FR-VER-006). |
| ZenML server and dashboard | Out | ZenML API | Run tracking, HTML report artifacts. |
| CLI | In | `tools.run`, `tools.validate_sources`; planned `tools.restore_snapshot`, `tools.forget` | |
| *Planned:* Vector DB (Qdrant) | Out/In | gRPC/HTTP | |
| *Planned:* LLM APIs (dataset generation, judging) | Out | HTTPS | Cost-capped. Content is sent to a third party, see OQ-05. |
| *Planned:* Model hub / registry (for example HF Hub, private) | Out | HTTPS | |
| *Planned:* Training compute (local GPU or cloud job) | Out | Provider SDK | |
| *Planned:* REST API and UI | In | HTTPS JSON, OpenAPI | Auth required (FR-UI-009, FR-INF-005). |
| *Planned:* Webhooks (GitHub) | In | HTTPS, HMAC-signed | P4 only. |
| *Planned:* Tracing (Opik) | Out | SDK | |

---

## 7. Risks

| ID | Risk | Likelihood / impact | Mitigation |
|---|---|---|---|
| RISK-01 | **Medium tag discovery may conflict with the "no bot-detection evasion" value and with Medium's terms.** The browser uses a logged-in persistent profile, randomised human-like pauses and mouse-wheel scrolling, and waits (headed) for a human to click a challenge. These read as evasion techniques even though article text comes only from RSS. | Medium / High (account ban, reputational) | Decide per OQ-01 before P1 exits. Recommended: RSS-only discovery as the default and only unattended mode (FR-MED-008); keep browser discovery only as an interactive opt-in with no manual challenge solving, or remove it. |
| RISK-02 | Training on third-party external content (Medium articles, PDFs of lecture notes and books) may breach copyright or licences. | Medium / High | FR-DS-006 default: external content is retrieval only. Record licences per source. |
| RISK-03 | Private material (diaries in a vault named `workDiaries`, a job-application test, colleagues' names) leaks into the training set or into answers to other people. | Medium / High | FR-OBS-004 opt-out flag, FR-FEA-008 masking, FR-PRV-004 third-party minimisation, FR-EVAL-005 safety tests, per-user isolation. |
| RISK-04 | Style contamination: external content mislabelled as `self` (vendored code in repos, quoted text and course notes in the vault, PDFs) makes the twin sound generic. | Medium / Medium | FR-ETL-005 (done for PDFs), FR-GH-006, FR-DS-008 style eligibility. |
| RISK-05 | No tests and no CI: regressions in parsers and keys stay silent, and a key-normalisation change could duplicate sources. | High / Medium | NFR-MNT-002 and FR-OPS-003 in P1, before the feature pipeline work starts. |
| RISK-06 | Full re-fetch each run (GitHub, Obsidian) costs rate limit and time, and blocks frequent triggers. | High / Medium | FR-REG-011, FR-REG-014 and FR-GH-005 change detection. |
| RISK-07 | Upstream deletions are never reflected (no tombstones), so the twin may use content the user deleted. | High / Medium | FR-ETL-010, FR-STO-006, FR-FEA-005. |
| RISK-08 | Medium feeds hold only about 10 posts, so tag coverage is limited and the corpus may skew towards recent posts. | High / Low | Accept, or add other sources per topic. Track topic counts against the cap in the summary (implemented). |
| RISK-09 | Concurrent runs (cron plus a manual or triggered run) collide on the browser profile or produce interleaved snapshots and commits. | Medium / Medium | FR-ORC-006 locking. |
| RISK-10 | A public repo with a proprietary licence and personal config is a confusing legal position and exposes personal data. | Medium / Medium | OQ-07, NFR-PRIV-002. |
| RISK-11 | Dataset generation sends personal content to a third-party LLM API. | Medium / Medium | OQ-05. Prefer local models or providers with no-retention terms. |
| RISK-12 | An immutable DVC history conflicts with deletion requests (right to erasure) for future users. | Low now, rising with multi-user / High | OQ-06, FR-VER-008. |
| RISK-13 | **Ownership takeover through shared owned-source keys.** GitHub keys are `github:user:<username>` (not user-scoped) and seeding `$set`s `owner_id`, so a second user who declares the owner's GitHub account becomes its owner, and the owner's code becomes that user's `self` data. Topics and `enabled` are similarly last-writer-wins. | Low now (one user), High at P4 / High | FR-REG-012, FR-REG-013, FR-UI-011. Implement the conflict check in P1 while it is cheap. |
| RISK-14 | **The ETL cannot run unattended as configured.** `medium.yaml` sets `headless: false` and the browser waits for a person, so the scheduler and triggers of P1 would hang or fail on a headless host. | High / Medium | FR-MED-008 and the OQ-01 decision before FR-TRG-002. |
| RISK-15 | **A bug in one extractor stops the whole ETL**, including versioning and the summary, because only `SourceError` is contained. | Medium / Medium | FR-ETL-012 with a fault-injection test. |
| RISK-16 | **Snapshots are write-only and committed before they are pushed.** A failed push leaves a commit whose data a fresh clone cannot fetch, and there is no restore path, so the "reproducible from `data_md5`" goal (G3) is not met yet. | Medium / High | FR-VER-006, FR-VER-007, FR-OPS-009. |

---

## 8. Open questions

| ID | Question | Why it matters / blocking | Needed by |
|---|---|---|---|
| OQ-01 | Keep browser-based Medium tag discovery (logged-in profile, human pacing, manual challenge clicks), or switch to RSS-only discovery? Recommendation: RSS-only for every unattended run; browser only as an interactive opt-in without manual challenge solving, or removed. | Compliance with NFR-CMP-002 and the unattended triggers (C6, RISK-14). Blocks FR-TRG-002 for Medium. | P1 |
| OQ-02 | Which base model, which licence, and what compute budget for SFT/DPO? | Drives FT, the size of the dataset to generate, and inference hosting. | P3 |
| OQ-03 | May external content (Medium free posts, PDFs, articles) be used for training, or only for retrieval? | FR-DS-006, RISK-02. | P3 |
| OQ-04 | Vector DB and embedding model choice (Qdrant? local vs hosted embeddings?), and should cleaned documents live in Mongo or only in vector payloads? | Blocks the FEA design. | P2 |
| OQ-05 | Which LLM may see personal content during dataset generation and judging (local only, or an API with no retention)? | Privacy, and the cost of the DS and EVAL stages. | P3 |
| OQ-06 | How to honour deletion for multiple users given immutable git and DVC history? | FR-PRV-002, FR-VER-008, RISK-12. | P4 |
| OQ-07 | Should the repo stay public? If yes, move personal paths and identifiers out of `configs/users/omar/` (for example to a private overlay) and reconcile with the proprietary licence. | NFR-PRIV-002, RISK-10. | P1 |
| OQ-08 | *Resolved by FR-ART-005:* an `article` with `origin=self` gets the declaring user's `owner_id`. | DQ-4. | P1 |
| OQ-09 | Where will a multi-user deployment run (owner's machine vs cloud), and how do remote users provide Obsidian vaults? | FR-OBS-005, FR-UI-005, NFR-SEC-002. | P4 |
| OQ-10 | Who are the twin consumers (only the owner, or recruiters and public)? Is a public-facing twin in scope? | FR-INF-005/006, FR-EVAL-005 scope. | P2 |
| OQ-11 | Should LinkedIn comments (replies to other people's posts) count as style data, given they lack context and include others' content? | Dataset quality and privacy (FR-DS-008). | P3 |
| OQ-12 | What target per-topic volume and freshness does RAG need, and should the 100-per-topic cap apply to providers other than Medium? | FR-ETL-008 scope. | P2 |
| OQ-13 | What are the monthly budgets for LLM APIs, embeddings, GPU and hosting? | NFR-COST-001, FR-OPS-008, FR-INF-008. | P2 |
| OQ-14 | Which authentication mechanism for the UI and API (OIDC with an external provider, or passwordless email)? | FR-UI-009, NFR-SEC-003. | P4 |

---

## 9. Traceability

For readability, the `FR-` prefix is left out of functional requirement IDs in this section (for example `ORC-007` means FR-ORC-007). NFR IDs keep their prefix.

### 9.1 Subsystems to pipeline stages

| Pipeline stage | Requirement groups | Main inputs → outputs | Phase |
|---|---|---|---|
| Configuration and registry | CFG, REG, UI-001..003, UI-009..012 | YAML or UI declarations → `users`, `sources`, `subscriptions` | P0, P1, P4 |
| Extraction (ETL) | ETL, MED, GH, LI, OBS, ART, TRG | registered sources → `RawDocument`s, `CrawlReport`, source state | P0, P1 |
| Raw storage and versioning | STO, VER-001..003, VER-006..008, ORC-001..004, ORC-006, ORC-007 | `RawDocument`s → `raw_documents`, DVC snapshot (`data_md5`), run record | P0, P1 |
| ETL → feature hand-off | ORC-008, STO-005, ETL-010, TRG-005 | upsert results and tombstones → change set | P1, P2 |
| Feature pipeline | FEA, ETL-011, VER-004, ORC-005 | change set → cleaned documents, chunks, vectors | P2 |
| Dataset generation | DS, VER-005, PRV-004 | cleaned documents (style-eligible self + licensed external) → dataset versions and cards | P3 |
| Training | FT | dataset versions → adapters in the model registry | P3 |
| Evaluation | EVAL, DS-009 | candidate model, curated sets → eval report, promotion decision | P2 (RAG), P3 (models) |
| Inference | INF, UI-008 | query + vectors + model → answer with citations and trace | P2, P3 |
| Operations | OPS, NFR-COST | traces, run records, cost ledger → alerts, dashboards, deployments, backups | P1, P2, P4 |
| Cross-cutting privacy | PRV, REG-010, REG-012, FT-005 | deletion and exclusion requests → purges across every store | P1, P2, P4 |

### 9.2 End-to-end chains
Each chain below must hold across stage boundaries. A chain is only as complete as its least-complete link.

| Chain | Links (in order) | Status at baseline |
|---|---|---|
| **Lineage** (G3) | ORC-007 run record → VER-001/002 `data_md5` → VER-006 pushed before commit → ORC-008 change set → VER-004 on cleaned docs, chunks, datasets → VER-005 dataset version → FT-004 model version → OPS-001 trace `model_version` | First two links implemented; the rest planned. Restore (VER-007) is needed to actually reproduce. |
| **Incremental update** (G6) | TRG-002/003 trigger → REG-014 cursor → REG-011 change detection → STO-005 changed flag → ORC-008 change set → TRG-005 → FEA-005 re-embed only changed | Planned. Today every run re-fetches GitHub, Obsidian and articles. |
| **Deletion** (owner deletes a note) | ETL-010 tombstone (complete enumeration only) → STO-006 → ORC-008 `tombstoned` → FEA-005 delete vectors → INF-002 never retrieves → DS-001 excluded from the next build → PRV-005 adapter flagged | Planned; no link exists. |
| **Exclusion** (user opts a document out) | OBS-004 / UI-006 / PRV-006 → STO-006 tombstone or exclude flag → same as the deletion chain from FEA-005 | Planned (glob exclusion at crawl time only). |
| **Account deletion** | PRV-002 → REG (user, subscriptions) → STO-006 purge by owner → FEA vectors → DS and FT artifacts → OPS traces → VER-008 snapshot partition → PRV-005 | Planned. |
| **Self/external split** (G2) | REG-004 / REG-012 / ART-005 owner assignment → ETL-005 origin → FEA-002 payload → DS-006 / DS-008 training eligibility → INF-002 retrieval filter | First two links implemented, with the REG-012 and ART-005 gaps. |
| **User isolation** (G5) | REG-012 → REG-010 → FEA-004 payload filter → INF-002/005 → DS build filter → FT-005 | Planned; precondition REG-012 not met. |
| **Cost control** (G7) | FEA-009, DS-007, FT-006, INF-008, UI-012 caps → OPS-008 ledger and hard stop → NFR-COST-001 budgets | Planned; no paid resource is used yet. |

### 9.3 Key dependencies between requirements
- FR-TRG-002 (scheduler) depends on FR-MED-008 (unattended mode) and OQ-01.
- FR-TRG-005 depends on FR-STO-005 and FR-ORC-008. It is placed in P2, with the feature pipeline it triggers.
- FR-TRG-006 depends on FR-REG-014 (`retry_not_before`).
- FR-ETL-010 depends on FR-STO-006 and, for GitHub, FR-GH-004 (truncation recorded).
- FR-REG-008 depends on FR-PRV-003 and FR-STO-006.
- FR-REG-010 and FR-FT-005 depend on FR-REG-012 (and, with the UI, FR-UI-011).
- FR-INF-003 depends on FR-FT-004. Until P3 the base model plus a style prompt is the normal path.
- FR-EVAL-004 is enforced by the training pipeline in P3 and by FR-OPS-004 in P4.
- FR-UI-* depend on FR-CFG-008, so that UI edits are not overwritten by YAML sync.

### 9.4 Counts by phase (functional requirements, excluding withdrawn)

| Phase | Implemented / Implemented (unverified) | Partial | Planned | Total |
|---|---|---|---|---|
| P0 | 45 | 0 | 0 | 45 |
| P1 | 0 | 8 | 30 | 38 |
| P2 | 0 | 3 | 28 | 31 |
| P3 | 0 | 0 | 22 | 22 |
| P4 | 0 | 0 | 25 | 25 |
| **All** | **45** | **11** | **105** | **161** (+1 withdrawn = 162 IDs) |

Each requirement is counted once, in its primary (first-listed) phase. Partial requirements are counted in the phase that closes their gap. FR-MED-003 (Implemented, on hold) and FR-LI-002 (Implemented, unverified) are counted in P0.
