# DigitalTwin: Software Requirements Specification (draft)

| | |
|---|---|
| Document status | Draft v0.1, for owner review |
| Date | 2026-10-23 |
| Baseline | `main` at `264cc1c` (ETL stage complete; later stages not started) |
| Owner | Omar Ayman Bakr |
| Reference | *LLM Engineer's Handbook* (Iusztin & Labonne). The book's stages are followed; its architecture is not copied. |

**Status legend** (applies to every FR)
- **Implemented**: the behaviour exists in code at the baseline commit and was checked by reading that code. Each one names the module that implements it.
- **Partial**: some of the behaviour exists. The gap is stated.
- **Planned**: no code exists yet. The requirement records intent and the acceptance criteria to build against.

Verification note: all *Implemented* claims were checked by reading code only. Nothing was run. The repo has no automated tests (there is no `tests/` directory), so no claim is backed by a test yet. See NFR-MNT-002.

---

## 1. Introduction

### 1.1 Purpose
This document states what the DigitalTwin system must do, from data collection to a deployed RAG and fine-tuned model. It also records which parts exist today. It is the basis for design decisions in the stages that are not built yet, and for the acceptance tests of each stage.

### 1.2 Product summary
DigitalTwin is an "LLM twin". It is a language model system that:
1. writes in the owner's voice (style learned from the owner's own writing: notes, code, posts), and
2. answers from the owner's knowledge (retrieval over the owner's writing plus curated external material).

The system is a chain of pipelines:

```
sources ─► ETL (raw_documents) ─► feature pipeline (clean/chunk/embed ─► vector DB)
                                         │
                                         ├─► dataset generation (instruction + preference)
                                         │        └─► fine-tuning (SFT ─► DPO) ─► model registry
                                         │                                           │
                                         └─────────────► RAG inference API ◄─────────┘
                                                              │
                                              monitoring / evaluation / CI/CD
```

### 1.3 Goals
- G1: Collect the owner's own writing and selected external knowledge from multiple platforms. Collection must be repeatable and idempotent, and must follow each platform's terms.
- G2: Keep a clean split between **self** content (style and voice) and **external** content (knowledge only). The split must hold through every later stage.
- G3: Produce versioned, reproducible datasets and models. Any model must be traceable to the data snapshot and code that produced it.
- G4: Serve a RAG-backed twin through an API with measured quality, latency and cost.
- G5: Grow from one user (the owner) to several users. Each user registers their own sources, and a shared source is ingested once.
- G6: Make ingestion event-driven, so that new content (for example a new post) reaches the twin without a manual full run.

### 1.4 Non-goals
- NG1: Bypassing paywalls, logins, member-only content, CAPTCHAs or other bot defences. Scraping platforms whose terms forbid it.
- NG2: Training a foundation model from scratch. Only fine-tuning of open-weight base models is in scope.
- NG3: A public, anonymous, multi-tenant SaaS. "Multi-user" means a small set of known, authenticated users.
- NG4: Impersonating the owner to third parties without disclosure, such as auto-posting to social platforms as the owner.
- NG5: Real-time streaming ingestion (sub-minute latency). Event triggers with minute-to-hour latency are enough.
- NG6: Redistributing third-party content collected as external knowledge.

### 1.5 Stakeholders and actors

| Actor | Type | Interest / interactions |
|---|---|---|
| **Owner** (Omar) | Primary user, operator, developer | Declares sources, runs pipelines, reviews data quality, trains and evaluates models, uses the twin. Today also the only admin. |
| **Future user** | Human, authenticated | Registers their own sources through a UI, subscribes to shared external sources, queries their own twin. Sees only their own data and twin. |
| **Admin** | Human role (initially the owner) | Manages users, global topics and provider settings. Disables abusive or broken sources. Handles deletion requests. |
| **Scheduler / trigger system** | System actor | Starts pipelines on a schedule, on platform events (webhooks or feed polling), or on user action. Calls the ETL with `source_ids`. |
| **Pipeline orchestrator** (ZenML) | System actor | Runs steps, tracks runs and artifacts, shows dashboards. |
| **External platforms** | External systems | Medium (RSS feeds, tag pages), GitHub REST API, LinkedIn (official data export only), web article hosts, local Obsidian vault filesystem. Later: LLM APIs for dataset generation and judging, model hubs, GPU or cloud providers. |
| **Third-party authors** | Indirect stakeholders | Their content is collected as external knowledge. They have interests in attribution, licensing and non-redistribution. |
| **Twin consumers** | Human | People who read the twin's output (for example a recruiter chatting with the twin). They need disclosure that the answer is AI-generated. |

---

## 2. Functional requirements

Requirement IDs are stable. New requirements get new IDs, and retired IDs are not reused.

Subsystem prefixes: CFG (configuration and topics), REG (source registry and multi-user), ETL (extraction framework), MED / GH / LI / OBS / ART (providers), STO (raw storage), ORC (orchestration and CLI), VER (data versioning), TRG (triggers and scheduling), UI (source registration UI and API), FEA (feature pipeline), DS (dataset generation), FT (fine-tuning), EVAL (evaluation), INF (RAG inference), OPS (LLMOps: monitoring, CI/CD, deployment), PRV (privacy and data-subject operations).

### 2.1 Configuration and topics (CFG)

| ID | Requirement | Acceptance criteria | Status |
|---|---|---|---|
| FR-CFG-001 | The system shall define topics in one file, `configs/topics.yaml`. Each topic maps to Medium tags and Obsidian tag prefixes. | Every topic key a source spec references is validated against `topics.yaml`. An unknown key fails loading with an error naming the key and the file (`BaseSourceSpec._check_topics`). | Implemented |
| FR-CFG-002 | The system shall load per-user declarations from `configs/users/<id>/profile.yaml` and `configs/users/<id>/sources/*.yaml`. Each declaration is validated against a discriminated union of source specs keyed by `type`. | An unknown `type`, an extra field (`extra="forbid"`) or an invalid value raises `ConfigValidationError` before any network access. | Implemented |
| FR-CFG-003 | The system shall reject a user declaration that lists the same canonical source twice. | A duplicate key raises a validation error that lists the duplicate keys (`UserDeclaration._no_duplicate_sources`). | Implemented |
| FR-CFG-004 | The system shall read secrets and environment settings only through one `Settings` object (`MONGO_*`, `GITHUB_*`, `DVC_*`, `RAW_STORE_*`). Real environment variables override `.env`, which overrides defaults. | `get_settings()` is the only reader of the environment. An invalid value (for example `MONGO_PORT=abc`) raises `ConfigValidationError`. Secrets are typed `SecretStr`. | Implemented |
| FR-CFG-005 | The system shall keep provider tuning (delays, caps, retries, browser options) in `configs/providers/<provider>.yaml`, separate from user declarations. | Changing `limit_per_topic` in `medium.yaml` changes behaviour with no code change. | Implemented |
| FR-CFG-006 | The system shall provide a health-check tool that validates all configuration and probes each provider, with an offline mode. | `tools/validate_sources.py` exits 1 on invalid config or an unhealthy provider. `--offline` makes no network calls. Writes `data/manifests/source_health.json`. | Implemented |
| FR-CFG-007 | Topic definitions shall be versioned with the data they label. Renaming or removing a topic shall migrate or flag the documents that carry it. | A removed topic key that still appears on stored documents is reported by the health check. | Planned |

### 2.2 Source registry and multi-user (REG)

| ID | Requirement | Acceptance criteria | Status |
|---|---|---|---|
| FR-REG-001 | The system shall store each source once, under a canonical key, however many users declare it. | Two users declaring `medium_tag: RAG` and `medium_tag: rag` produce one `sources` record `medium:tag:rag` and two `subscriptions` (`registry/keys.py`, `RegistrySeeder`). | Implemented |
| FR-REG-002 | Canonical keys shall normalise equivalent inputs. URLs: lower-cased scheme and host, no fragment, no trailing `/`, tracking parameters (`utm_*`, `mc_*`, `fbclid`, `gclid`, `ref`, `source`) removed, query sorted. Handles and tags: trimmed and lower-cased. Medium handles get an `@` prefix. | `article_key("https://X.com/a/?utm_source=t#h") == article_key("https://x.com/a")`. | Implemented |
| FR-REG-003 | The system shall model users (`id`, `name`, `handles`), sources and many-to-many subscriptions. Uniqueness of `(user_id, source_id)` shall be enforced in storage. | A unique index exists on `subscriptions(user_id, source_id)` (`MongoRegistryStore.setup`). | Implemented |
| FR-REG-004 | Sources holding a user's own writing (GitHub, Obsidian, LinkedIn) shall carry `owner_id`. External sources (Medium, articles) shall be shared and carry no owner. | `Source.from_spec` sets `owner_id` only when `spec.owned` is true. | Implemented |
| FR-REG-005 | Seeding the registry from declarations shall be idempotent. | Running `sync_registry` twice with unchanged YAML reports `sources_new=0`, `subscriptions_new=0` on the second run. | Implemented |
| FR-REG-006 | The registry shall keep the latest crawl state for each source: status (`never`/`ok`/`failed`), last run id, timestamp, error, and item counts. | After a run, every crawled source has `state.last_run_id` equal to that run's id (`record_states`). | Implemented |
| FR-REG-007 | Selecting sources for a run shall support three modes: all enabled sources; one user's subscribed enabled sources; an explicit list of source ids (optionally checked against a user's subscriptions). | An unknown user raises `UnknownUserError`. An unknown source id, or one the user is not subscribed to, raises `UnknownSourceError` before crawling (`SourceSelector`). | Implemented |
| FR-REG-008 | A user shall be able to unsubscribe from a source. A shared source with no subscribers left shall be disabled, and its documents kept or purged according to FR-PRV-003. | After the last unsubscribe the source has `enabled=false` and is not selected by any run. | Planned. The seeder only upserts; a source removed from YAML stays in the registry. |
| FR-REG-009 | Removing a source from a user's YAML or UI shall be applied to the registry: the subscription is deleted, and the source is not left stale. | Sync shows `subscriptions_removed=n` and the selector no longer returns the source for that user. | Planned |
| FR-REG-010 | The system shall support several users with isolated own-content. A user's `self` documents, datasets, adapters and twin shall never be visible to, or trained into, another user's twin. | A query for user B's twin never retrieves a document with `owner_id=A`. Dataset builds filter by `owner_id`. | Partial. `owner_id` exists on documents and sources; nothing enforces isolation yet. |
| FR-REG-011 | The system shall skip re-ingesting a source whose content has not changed since its last successful crawl, where the platform allows change detection (ETag, `updated_at`, feed GUIDs, file mtime and hash). | A second run with no upstream changes performs no full-content fetches for GitHub files whose blob SHA is unchanged and no writes for unchanged Obsidian notes. The report shows them as `skipped: unchanged`. | Partial. Documents dedupe by stable id, and Medium skips documents already stored for the same topics. GitHub, Obsidian and articles re-fetch everything on each run. `content_hash` is stored but not used to skip work. |

### 2.3 Extraction framework (ETL)

| ID | Requirement | Acceptance criteria | Status |
|---|---|---|---|
| FR-ETL-001 | Every provider shall implement one abstract extractor contract: an optional shared `session()`, `extract_source(source)` yielding `RawDocument`s, and `health_check(offline)`. | `BaseExtractor` subclasses exist for medium, github, linkedin, obsidian and articles, registered in `raw_data/sources/registry.py`. | Implemented |
| FR-ETL-002 | Errors shall be isolated by level. An item-level error is recorded and skipped. A source-level `SourceError` marks that source failed and the run continues with the next source. `AccessBlockedError`, `AuthenticationError` and `RateLimitError` stop the provider and mark the remaining sources "not crawled". `ConfigError` stops before fetching. | Error handling in `BaseExtractor.extract` and `_abort`. A source whose every attempted item failed is marked failed (`_fail_sources_without_successes`). | Implemented |
| FR-ETL-003 | Every crawl shall produce a `CrawlReport` with one outcome per item (`ok`/`failed`/`skipped` plus a reason) and one error per failed source. | The report is rendered as HTML per provider in the ZenML dashboard (`steps/etl/html_report.py`). | Implemented |
| FR-ETL-004 | Every document shall conform to one `RawDocument` contract: stable `id` (`{source}:{native_id}`), `provider`, `source` kind, `owner_id`, `source_ids`, `origin` (`self`/`external`), `title`, markdown `content`, `url`, `author`, `created_at`/`updated_at`, `content_hash` (sha256), `topics`, `provenance[]`, `metadata`. | All extractors build documents through `BaseExtractor.make_document`. | Implemented |
| FR-ETL-005 | Third-party material found inside a user's own source (for example PDFs in the vault) shall be marked `origin=external` and get no `owner_id`. | Obsidian PDFs use `pdf_origin` (default `external`), and `make_document(owned=False)` drops `owner_id`. | Implemented |
| FR-ETL-006 | Each document shall record provenance: source id, query or page, rank, run id, and collection time. The last 50 sightings are kept. | `$push` with `$slice: -50` on upsert. | Implemented |
| FR-ETL-007 | Topic assignment shall combine declared source topics, platform tags mapped through `topics.yaml`, and path or repo glob rules. | Medium: tag-source topics plus mapped tags. Authors: intersection with followed topics. Obsidian: tag prefixes plus `topic_rules`. GitHub: `topic_rules` on repo name. | Implemented |
| FR-ETL-008 | Per-topic caps (`limit_per_topic`, default 100) shall hold across runs for capped providers. Counts already in the store count toward the cap. | A Medium run with every topic of a source at cap records `skipped: topics [...] already at cap` and fetches nothing for that source. | Implemented (Medium only) |
| FR-ETL-009 | Documents shall be written in batches of 50 during extraction, so a crash loses at most one unflushed batch. | `BATCH_SIZE=50` and `finally: flush()` in `steps/etl/crawl.py`. | Implemented |
| FR-ETL-010 | Content that disappears upstream (a deleted note, repo, file or post) shall be detected and marked `deleted_at` (a tombstone), not left as live data. | After a note is deleted from the vault, the next run marks its document deleted. The feature pipeline excludes it and removes its vectors. | Planned |
| FR-ETL-011 | Near-duplicate content reachable under different ids (the same article via two URLs or a feed and a page, or a README mirrored in docs) shall be detected by `content_hash` or near-duplicate hashing. | A dedup report lists groups that share `content_hash`. Downstream stages use one representative per group. | Planned |

### 2.4 Providers

#### Medium (MED)
| ID | Requirement | Acceptance criteria | Status |
|---|---|---|---|
| FR-MED-001 | Article text shall come only from Medium's official RSS feeds (author or publication). Article pages shall not be scraped. | `MediumFeedClient` is the only source of `content`. | Implemented |
| FR-MED-002 | Member-only stories (the feed has a preview only) shall be skipped, even when the crawler profile is logged in. | `skip_member_only: true`. Outcome: `skipped: member-only story`. | Implemented |
| FR-MED-003 | `medium_tag` sources shall discover the tag's top article links with a browser at human pace. If a bot challenge does not clear, discovery shall fall back to the tag's RSS feed for the rest of the run. | `listing_blocked` flag in `MediumExtractor._discover`. | Implemented (see RISK-01 on compliance) |
| FR-MED-004 | `medium_author` sources shall read the author's feed with no browser. | The browser is started only if a `medium_tag` source is selected. | Implemented |
| FR-MED-005 | Feed requests shall be paced (`feed_delay_s`, default 3 s) and back off on HTTP 429 and 5xx, up to `feed_max_retries`. After that a `RateLimitError` stops the provider. | `feed_client.py`. | Implemented |
| FR-MED-006 | Articles found on a tag page but missing from the author's feed (older than about the last 10 posts) shall be recorded as skipped with that reason. | Outcome reason `not in <feed> (feeds carry only the latest ~10 posts)`. | Implemented |
| FR-MED-007 | The owner's own Medium posts (if any) shall be ingested as `origin=self` with `owner_id`. | A `medium_author` spec flagged as the user's own produces `self` documents. | Planned. All Medium content is `external` today. |

#### GitHub (GH)
| ID | Requirement | Acceptance criteria | Status |
|---|---|---|---|
| FR-GH-001 | The system shall ingest README, markdown, Python and notebook files from a user's repositories through the GitHub REST API, with include/exclude globs, fork and hidden-path filters, a size limit (`max_file_kb`) and a minimum length (`min_chars`). | `GitHubExtractor`, `github/files.py`. | Implemented |
| FR-GH-002 | Notebooks shall be converted to markdown (markdown and code cells, no outputs). | `github/notebook.py`. | Implemented |
| FR-GH-003 | An optional token shall raise rate limits. Exhausted limits (403/429 with `X-RateLimit-Remaining: 0`) shall raise `RateLimitError` with `retry_after`. | `github/client.py`. | Implemented |
| FR-GH-004 | Truncated repository trees shall be logged as a warning. | Warning text "file tree truncated". | Implemented |
| FR-GH-005 | Unchanged files shall not be re-downloaded (compare blob SHA with the stored metadata). | See FR-REG-011. | Planned |
| FR-GH-006 | Only content the user authored shall count as `self`. Vendored or third-party code inside repos shall be excludable, and should be detected (for example by LICENSE headers or known vendored paths). | A vendored file is either excluded or ingested as `external`. | Partial. Exclusion is by glob only. |

#### LinkedIn (LI)
| ID | Requirement | Acceptance criteria | Status |
|---|---|---|---|
| FR-LI-001 | LinkedIn content shall be ingested only from the user's official data export, unzipped to `export_dir`. LinkedIn shall never be scraped. | `LinkedInExportSpec`, `linkedin/export_files.py`. | Implemented |
| FR-LI-002 | Posts, articles and comments shall be parsed into `linkedin_post`, `linkedin_article` and `linkedin_comment` documents (`origin=self`), with hashtags mapped to topics. | `linkedin/parsers.py`. | Implemented in code; not yet run on real data (export pending). |
| FR-LI-003 | A missing export directory shall fail only that source, with a clear message. | `SourceUnavailableError` names the path. | Implemented |
| FR-LI-004 | A user shall be able to upload a LinkedIn export zip through the UI. The system unpacks it to the user's export directory and triggers ingestion. | Upload, then the run starts within 1 minute. The zip is deleted after extraction. | Planned |

#### Obsidian (OBS)
| ID | Requirement | Acceptance criteria | Status |
|---|---|---|---|
| FR-OBS-001 | The system shall ingest notes from a local vault with include, exclude and hidden-path globs, a minimum length, and markdown cleanup. | `ObsidianExtractor`, `obsidian/markdown.py`. | Implemented |
| FR-OBS-002 | PDFs matching `pdf_include` shall be extracted (PyPDF) as `external` by default, with a size limit (`pdf_max_mb`). | `_pdf_document`. | Implemented |
| FR-OBS-003 | A missing vault shall fail only that source. | `SourceUnavailableError("vault not found")`. | Implemented |
| FR-OBS-004 | Private or sensitive notes shall be excludable by glob, and also by a frontmatter flag (for example `twin: false` or `private: true`). | A note with `private: true` is skipped with reason `private`. | Partial. Glob exclusion only (for example `images/Vodafone*`). |
| FR-OBS-005 | Obsidian ingestion shall run only on the machine that holds the vault. Remote or multi-user setups shall need an explicit upload or sync mechanism. | See UI-005. | Planned |

#### Articles (ART)
| ID | Requirement | Acceptance criteria | Status |
|---|---|---|---|
| FR-ART-001 | The system shall ingest single public web pages by URL (plain HTTP, no JavaScript) and convert them to markdown. Pages below `min_chars` (default 200) fail the source. | `CustomArticleCrawler`, `ArticlesExtractor`. | Implemented |
| FR-ART-002 | Requests shall be paced (`request_delay_s`, 1 req/s) and sent with an identifying User-Agent. | `articles.yaml`, `custom_article_crawler.py`. | Implemented |
| FR-ART-003 | The crawler shall check `robots.txt` before fetching and refuse disallowed URLs, recording `skipped: robots.txt`. | A URL disallowed for the crawler's UA is not fetched. | Planned |
| FR-ART-004 | Article authors shall be extracted from page metadata where present. The site host is the fallback. | `author` equals the byline for pages with `<meta name="author">`. | Partial. Host only. |

### 2.5 Raw storage (STO)

| ID | Requirement | Acceptance criteria | Status |
|---|---|---|---|
| FR-STO-001 | Raw documents shall be stored behind an abstract `RawDataStore`, with the backend chosen by configuration (`RAW_STORE_BACKEND`). | `raw_data/store/{base,factory,mongo_store}.py`. | Implemented |
| FR-STO-002 | Upserts shall be idempotent by `_id`. Scalar fields are replaced. `topics` and `source_ids` are merged with `$addToSet`. Provenance is appended and capped at 50. | Re-running the same crawl changes no document count. `matched` grows and `inserted` is 0. | Implemented |
| FR-STO-003 | Indexes shall exist on `provider`, `owner_id`, `source_ids`, `topics` and `origin`. | `MongoRawDataStore.setup`. | Implemented |
| FR-STO-004 | Reading back a malformed record shall raise `StoreCorruptedError` with its location. | `_to_document`. | Implemented |
| FR-STO-005 | Content changes shall be detectable. When `content_hash` differs from the stored value, the document shall be flagged changed (for example `changed_at`), so the feature pipeline re-processes only changed documents. | After an upstream edit, the next feature run re-embeds only that document. | Planned |

### 2.6 Orchestration and CLI (ORC)

| ID | Requirement | Acceptance criteria | Status |
|---|---|---|---|
| FR-ORC-001 | The ETL shall run as a ZenML pipeline `digital_data_etl(user_id, source_ids)`: sync_registry → select_sources → crawl_{medium,github,linkedin,obsidian,articles} → version_raw_data → summarize. Caching is disabled. | `pipelines/digital_data_etl.py`. | Implemented |
| FR-ORC-002 | A CLI shall start the ETL for all sources, one user, or explicit source ids, with a timestamped run name. | `uv run python -m tools.run --etl [--user U] [--source ID ...]`. | Implemented |
| FR-ORC-003 | Each provider step shall return a summary: status `ok`/`partial`/`failed`/`skipped`, source and item counts, inserted and matched counts, stored total, and per-topic counts against the cap. | `crawl_provider` summary dict. | Implemented |
| FR-ORC-004 | The run shall fail (`PipelineError`) after all steps finish if any provider status is `failed` or versioning failed. `partial` is a warning. Crawled data is kept in every case. | `summarize_crawl`. | Implemented |
| FR-ORC-005 | Later stages (feature, dataset, training, evaluation, deployment) shall each be a separate ZenML pipeline with typed artifacts. Each shall take the upstream data or model version as an explicit input. | Each pipeline run's metadata records the input version ids. | Planned |
| FR-ORC-006 | Two runs that would crawl the same source shall not run concurrently. The second run shall wait or skip that source. | A lock per source (or per provider for the browser profile) is held during the crawl. A concurrent run reports `skipped: locked`. | Planned |

### 2.7 Data versioning (VER)

| ID | Requirement | Acceptance criteria | Status |
|---|---|---|---|
| FR-VER-001 | After each ETL run, the system shall export a deterministic snapshot: one JSONL per provider and one per registry collection, sorted by id with sorted keys, and written atomically. Provenance and source state are excluded so diffs stay meaningful. | `RawDataSnapshotExporter`. Two exports of the same store are byte-identical. | Implemented |
| FR-VER-002 | The snapshot shall be `dvc add`-ed. The pointer and DVC setup files shall be git-committed (`data: raw snapshot <run_id>`) and pushed to the configured DVC remote. Each action can be switched off by setting. | `version_raw_data` step. `DVC_ENABLED`, `DVC_AUTO_COMMIT`, `DVC_AUTO_PUSH`. Commits `264cc1c`, `d644b8b`, `088c488`. | Implemented |
| FR-VER-003 | A versioning failure shall be reported but shall not roll back or corrupt stored data. | `status: failed` in the summary. The store is untouched. | Implemented |
| FR-VER-004 | Every downstream artifact (cleaned docs, chunks, embeddings collection, instruction and preference datasets, adapters, eval reports) shall record the raw snapshot hash (`data_md5`) and git commit it came from. | Given a model version, `dvc checkout` of the recorded hash reproduces its training input. | Planned |
| FR-VER-005 | Datasets for training shall be versioned and published as immutable named versions (for example on the Hugging Face Hub, private, or a DVC remote). | `dataset@vN` cannot be overwritten. Every new build gets a new version. | Planned |

### 2.8 Triggers and scheduling (TRG)

| ID | Requirement | Acceptance criteria | Status |
|---|---|---|---|
| FR-TRG-001 | The ETL shall accept an explicit list of source ids, so that triggers can run just the affected sources. | `digital_data_etl(source_ids=[...])`. | Implemented (entry point only) |
| FR-TRG-002 | A scheduler shall run the ETL on a configurable cadence for each provider (for example GitHub daily, Medium tags weekly). | The schedule is defined in config. Runs appear in ZenML with `trigger=schedule`. | Planned |
| FR-TRG-003 | Event triggers shall start ingestion of only the affected source when the user publishes new content. Mechanisms: GitHub `push` webhook (or polling `pushed_at`), Medium author-feed polling (new GUID), Obsidian file watcher (debounced), LinkedIn export upload. | A new commit to a tracked repo leads to an ETL run for `github:user:<u>` within 15 minutes (webhook) or one polling interval. | Planned |
| FR-TRG-004 | Triggers shall be debounced and coalesced. Several events for the same source inside a window shall cause one run. | 10 vault saves within 5 minutes cause 1 run. | Planned |
| FR-TRG-005 | A successful ETL run that changed data shall be able to trigger the feature pipeline for the changed documents only. | `inserted+changed > 0` causes a feature run scoped to those ids. | Planned |
| FR-TRG-006 | Triggers shall respect provider backoff. A provider that ended with `RateLimitError(retry_after)` or `AccessBlockedError` shall not be retried before `retry_after`, or before a cool-down (default 24 h) for blocked access. | No run for that provider starts during the cool-down. The scheduler log shows `deferred`. | Planned |
| FR-TRG-007 | Webhook endpoints shall verify signatures (for example the GitHub `X-Hub-Signature-256` HMAC) and reject unsigned or replayed requests. | An invalid signature returns 401 and no run starts. | Planned |

### 2.9 Source registration UI and API (UI)

| ID | Requirement | Acceptance criteria | Status |
|---|---|---|---|
| FR-UI-001 | An authenticated user shall be able to add a source through a form backed by the same Pydantic spec models used by YAML. | Invalid input shows the field-level validation message from the spec model. A valid one creates or reuses the canonical source and a subscription. | Planned (the spec models were designed for this: "YAML today, a UI form later") |
| FR-UI-002 | When a user adds a source that already exists (same canonical key), the UI shall subscribe them to it and shall not create or crawl a duplicate. | The UI shows "already tracked, last crawled <ts>". No new source record is created. | Planned |
| FR-UI-003 | The UI shall list the user's subscriptions with crawl state (status, last crawl, error, item counts) read from the registry. | Values match `sources.state` for that source. | Planned |
| FR-UI-004 | The UI shall let a user trigger an on-demand crawl of their own sources, rate-limited per user (for example 1 run per source per hour). | The button is disabled during the cool-down. The API returns 429 when the limit is exceeded. | Planned |
| FR-UI-005 | The UI shall support connecting own-content sources: GitHub (OAuth or token, read-only scope), LinkedIn export upload, and Obsidian vault upload or sync (zip or a git remote). | Credentials are stored encrypted. Revoking them removes them and disables dependent sources. | Planned |
| FR-UI-006 | The UI shall let a user mark sources or documents as excluded from training and/or retrieval, and see what the twin was trained on. | An excluded document is absent from the next dataset and vector index builds. | Planned |
| FR-UI-007 | An admin view shall manage users, topics, provider settings, and globally disabled sources. | Only users with role `admin` can reach it. | Planned |
| FR-UI-008 | All UI operations shall be available through a versioned REST API (`/api/v1/...`) with an OpenAPI schema. | The OpenAPI document is served. The UI uses only the public API. | Planned |

### 2.10 Feature pipeline (FEA)

| ID | Requirement | Acceptance criteria | Status |
|---|---|---|---|
| FR-FEA-001 | A feature pipeline shall read raw documents (all, by user, by provider, or by changed ids) and produce cleaned documents. Cleaning removes boilerplate, normalises whitespace and unicode, strips non-content markup, removes emoji and URL noise where it does not carry meaning, and keeps code blocks intact. | A cleaned document stores `raw_id`, `content_hash_raw`, and `cleaner_version`. Golden-file tests pass for each source kind. | Planned |
| FR-FEA-002 | Chunking shall depend on the source kind: markdown or notes split by headings and token window; code split by function or class; posts and comments kept whole when below the window. Chunk size and overlap are configurable. | Defaults are recorded in config. No chunk exceeds the embedding model's max tokens. Every chunk carries `document_id`, `owner_id`, `origin`, `topics`, `source kind`, `url`, `position`. | Planned |
| FR-FEA-003 | Chunks shall be embedded with a configurable embedding model, recorded by name, version and dimension. | Changing the model creates a new vector collection, so dimensions and models are never mixed. | Planned |
| FR-FEA-004 | Embeddings and metadata shall be stored in a vector database (candidate: Qdrant) with payload filters on `owner_id`, `origin`, `topics`, `kind`. | A filtered search with `owner_id=X` returns only X's self chunks plus shared external chunks. | Planned |
| FR-FEA-005 | The feature pipeline shall be incremental and idempotent. Re-running on unchanged data writes nothing. Changed documents replace their chunks. Tombstoned documents have their vectors deleted. | Point ids are deterministic (hash of `document_id` and `chunk_index`). A second run makes 0 upserts. | Planned |
| FR-FEA-006 | Cleaned documents and chunks shall be stored (or snapshotted) so that dataset generation does not re-clean. | A `cleaned_documents` collection or vector payload contains the full cleaned text. | Planned |
| FR-FEA-007 | The pipeline shall drop or quarantine low-quality content: empty after cleaning, below a minimum length, mostly non-language (for example a minified file or base64), or a duplicate by `content_hash`. | The quarantine count appears in the run summary with reasons. | Planned |
| FR-FEA-008 | PII scrubbing shall run on content before it enters training datasets. Emails, phone numbers, addresses, API keys and tokens shall be detected and masked. Secrets shall also be masked in the vector index. | A seeded test document with a fake API key and phone number comes out masked. A secret scanner finds 0 hits in the dataset. | Planned |

### 2.11 Dataset generation (DS)

| ID | Requirement | Acceptance criteria | Status |
|---|---|---|---|
| FR-DS-001 | The system shall generate an instruction dataset (instruction → answer) from the user's cleaned content, using an LLM to write instructions for content chunks. `self` content teaches style. `external` content may be used only for knowledge-type samples, and only if FR-DS-006 allows it. | Each sample stores `owner_id`, `source document ids`, `origin`, `generator model`, `prompt version`. | Planned |
| FR-DS-002 | The system shall generate a preference dataset (prompt, chosen, rejected) for DPO. `chosen` reflects the user's voice (derived from their own text). `rejected` is a generic or off-style answer. | Each sample has a non-identical chosen/rejected pair. Their origin is recorded. | Planned |
| FR-DS-003 | Generated samples shall be filtered: deduplicated (exact and near), length-bounded, and checked by rules and/or an LLM judge for faithfulness to the source chunk. | A filter report lists counts removed per rule. The removal rate is reported. | Planned |
| FR-DS-004 | Datasets shall be split train/test by source document, never by sample, so no document appears in both. | A leakage check finds 0 shared `document_id`s across splits. | Planned |
| FR-DS-005 | Datasets shall be versioned (FR-VER-005), with a dataset card: sources, counts per topic and kind, generator model, filters, and licence notes. | The card is generated automatically with each version. | Planned |
| FR-DS-006 | Third-party (`external`) content shall enter training datasets only if its licence permits. Otherwise it is limited to RAG retrieval. The default is retrieval only. | The dataset build excludes `external` documents unless `license_allows_training=true` is recorded for the source. | Planned (see Open Question OQ-03) |
| FR-DS-007 | The cost of LLM calls for generation shall be estimated before a run and capped by configuration. | A run aborts when the estimated cost exceeds `max_usd`. Actual cost is logged. | Planned |

### 2.12 Fine-tuning (FT)

| ID | Requirement | Acceptance criteria | Status |
|---|---|---|---|
| FR-FT-001 | The system shall fine-tune an open-weight base model (candidate: an 8B-class model, with LoRA or QLoRA) with SFT on the instruction dataset. | The training run logs the base model, dataset version, hyperparameters, seed, and loss curves. The adapter is saved. | Planned |
| FR-FT-002 | The system shall then run preference alignment (DPO) on the preference dataset, starting from the SFT checkpoint. | The DPO run references the parent SFT model version. | Planned |
| FR-FT-003 | Training shall be reproducible from recorded inputs: base model revision, dataset version, config, seed, and library versions. | A re-run from the recorded config lands within ±2% of the reference eval scores. | Planned |
| FR-FT-004 | Trained models and adapters shall be registered with metadata and lineage (data snapshot, dataset version, parent model, eval report). They shall be stored privately. | Registry entries are immutable. Promotion uses tags (`staging`, `production`). | Planned |
| FR-FT-005 | One adapter shall be trained per user. A user's adapter shall never be trained on another user's `self` data. | The dataset filter is checked in the pipeline (FR-REG-010). | Planned |
| FR-FT-006 | Training shall run on configurable compute (local GPU or a cloud GPU job), with a cost and time budget. | The job is cancelled when it exceeds `max_hours`. | Planned |

### 2.13 Evaluation (EVAL)

| ID | Requirement | Acceptance criteria | Status |
|---|---|---|---|
| FR-EVAL-001 | Each candidate model shall be evaluated on the held-out split for: style similarity to the user (LLM judge and/or a stylometric classifier), answer relevance, and factual faithfulness. | The eval report stores per-metric scores with confidence intervals. | Planned |
| FR-EVAL-002 | General-capability regression shall be measured on at least one public benchmark subset, to detect catastrophic forgetting. | A drop greater than a configured threshold (for example 5 points) blocks promotion. | Planned |
| FR-EVAL-003 | The RAG system shall be evaluated on a curated question set: retrieval (recall@k, MRR) and generation (faithfulness, answer relevance, context precision). | A test set of at least 100 questions with reference sources. Metrics are reported per topic. | Planned |
| FR-EVAL-004 | Promotion to `production` shall require passing configured thresholds against the current production model. | Gating is enforced in the CI/CD pipeline (FR-OPS-004). | Planned |
| FR-EVAL-005 | Safety checks shall verify that the twin refuses or deflects requests to reveal private data or secrets, and discloses it is an AI when asked. | A red-team prompt set reaches a pass rate at or above a threshold. | Planned |

### 2.14 RAG inference service (INF)

| ID | Requirement | Acceptance criteria | Status |
|---|---|---|---|
| FR-INF-001 | The system shall expose an HTTP API (for example `POST /api/v1/twins/{user_id}/chat`) that takes a query and optional conversation history and returns an answer with cited sources. | The response contains `answer`, `sources[]` (document id, title, url, origin), `model_version`, `trace_id`. | Planned |
| FR-INF-002 | Retrieval shall support query expansion or rewriting, self-query metadata extraction (topic, kind), filtered vector search scoped to the user, and reranking. | Retrieval returns only chunks with `owner_id ∈ {user, null}`. The reranker cuts to top-k (configurable). | Planned |
| FR-INF-003 | Generation shall use the user's fine-tuned model, falling back to the base model plus a style prompt if it is unavailable. The model version shall be reported. | When the adapter fails to load, the fallback answer carries `model_version=fallback`. | Planned |
| FR-INF-004 | The service shall support streaming responses. | First token arrives within the NFR-PERF-004 budget. | Planned |
| FR-INF-005 | Requests shall be authenticated, and a user shall reach only their own twin unless that twin is explicitly shared publicly. | A request with another user's id returns 403. | Planned |
| FR-INF-006 | Every answer shall carry an AI-generated disclosure for twin consumers. | The disclosure field or banner is present in the API and UI. | Planned |

### 2.15 LLMOps: monitoring, CI/CD, deployment (OPS)

| ID | Requirement | Acceptance criteria | Status |
|---|---|---|---|
| FR-OPS-001 | Every inference request shall be traced: prompt template version, retrieved chunk ids, model version, latency per stage, token counts, cost (candidate: Opik, already a declared dependency). | A trace is viewable by `trace_id`. 100% of requests are traced (sampling is configurable). | Planned (`opik` is in `pyproject.toml` but not imported anywhere) |
| FR-OPS-002 | Prompt templates shall be versioned and referenced by version in traces. | Changing a template bumps its version. Traces show the version used. | Planned |
| FR-OPS-003 | CI shall run on every push: lint (ruff), type check (mypy), unit tests, config validation (`validate_sources --offline`) and a secret scan. | The CI workflow exists. Merging to `main` is blocked on failure. | Planned (no `.github/`, no tests) |
| FR-OPS-004 | CD shall build and deploy the inference service as a container. The model is promoted through `staging` → `production` with eval gating (FR-EVAL-004) and one-step rollback. | Rollback to the previous model version takes ≤ 5 minutes. | Planned |
| FR-OPS-005 | Online monitoring shall alert on: error rate, p95 latency, cost per day, retrieval empty-result rate, and (sampled) LLM-judge quality drift. | Alert thresholds are configured. A test alert fires. | Planned |
| FR-OPS-006 | Pipeline monitoring shall alert when an ETL provider ends `failed`, or the same source fails on N consecutive runs (default 3). | An alert names the source and the last error from `sources.state`. | Planned |
| FR-OPS-007 | User feedback (thumbs up/down, corrections) on answers shall be captured and linked to the trace, for later preference data. | Feedback is stored with `trace_id`. It can be exported into a DPO candidate set. | Planned |

### 2.16 Privacy and data-subject operations (PRV)

| ID | Requirement | Acceptance criteria | Status |
|---|---|---|---|
| FR-PRV-001 | A user shall be able to export all data held about them: registry records, own documents, datasets and model lineage. | The export contains every document with `owner_id=user`. | Planned |
| FR-PRV-002 | A user shall be able to delete their account. This removes their user record, subscriptions, own documents, chunks and vectors, own datasets and adapters, and their traces. It shall also cover future DVC snapshots and document how past snapshots are handled. | After deletion, queries for `owner_id=user` return 0 across Mongo and the vector DB. A deletion log entry exists. | Planned (see OQ-06 on immutable snapshots) |
| FR-PRV-003 | When a shared external source loses its last subscriber, its documents shall be retained or purged by a configurable policy. | The policy is applied at sync, and the result is reported. | Planned |
| FR-PRV-004 | Third-party personal data in own content (names or emails of others in comments, notes or diaries) shall be minimised before training. | Covered by the PII scrubbing in FR-FEA-008. | Planned |

---

## 3. Non-functional requirements

### 3.1 Performance (PERF)
| ID | Requirement | Measure |
|---|---|---|
| NFR-PERF-001 | A full ETL of the owner's current sources shall complete in one unattended run. | ≤ 3 h wall-clock for about 2.6k documents with default pacing. Measured from ZenML run duration. |
| NFR-PERF-002 | A single-source triggered ETL (one GitHub account, one author feed) shall complete quickly. | ≤ 10 min (GitHub with change detection) and ≤ 2 min (one feed). |
| NFR-PERF-003 | The feature pipeline shall handle incremental updates efficiently. | ≤ 5 min for ≤ 100 changed documents on owner hardware. |
| NFR-PERF-004 | RAG API latency (non-streaming, excluding cold start). | p95 ≤ 5 s end-to-end. Time to first token (streaming) p95 ≤ 1.5 s. Retrieval stage p95 ≤ 300 ms. |
| NFR-PERF-005 | Vector search shall scale to the expected corpus size. | ≥ 100k chunks with p95 search ≤ 100 ms. |

### 3.2 Reliability and idempotency (REL)
| ID | Requirement | Measure / status |
|---|---|---|
| NFR-REL-001 | Every pipeline shall be idempotent. Re-running with the same inputs and unchanged upstream data produces no new records and no duplicate vectors. | ETL: **Implemented** (stable ids, upserts, `$addToSet`). Downstream: Planned. |
| NFR-REL-002 | A failure in one source or provider shall not prevent the others from running or losing their data. | **Implemented** (error levels, batch flush in `finally`, `summarize` raises only at the end). |
| NFR-REL-003 | A crash mid-run shall lose at most one batch (50 documents) of extracted data per provider. | **Implemented** (`BATCH_SIZE=50`). |
| NFR-REL-004 | Snapshot writes shall be atomic. | **Implemented** (`.tmp` plus `os.replace`). |
| NFR-REL-005 | External calls shall use timeouts and bounded retries with backoff. No unbounded waits. | **Partial**: Medium feeds (retries), browser (page-load timeout, challenge timeout), Mongo (`timeout_ms=5000`). GitHub has no automatic retry. Articles have no explicit timeout config. |
| NFR-REL-006 | The inference service shall reach 99% monthly availability once deployed (single-user scale). | Planned. Measured by uptime checks. |

### 3.3 Scalability (SCL)
| ID | Requirement | Measure |
|---|---|---|
| NFR-SCL-001 | The registry design shall support at least 50 users and 5k sources without schema change. Shared sources are crawled once regardless of subscriber count. | Dedup is **Implemented**. Crawl cost scales with unique sources, not subscriptions. |
| NFR-SCL-002 | Storage backends (raw store, registry, vector DB) shall be swappable behind interfaces. | **Implemented** for the raw store and registry (abstract base plus factory). Planned for the vector DB. |
| NFR-SCL-003 | Provider steps shall be parallelisable across providers. | Planned (the steps are independent in the DAG; currently they run on the local orchestrator). |

### 3.4 Security (SEC)
| ID | Requirement | Measure / status |
|---|---|---|
| NFR-SEC-001 | Secrets shall never be committed or logged. | `.env*` is git-ignored. `SecretStr`. `display_uri` masks the Mongo password: **Implemented**. A CI secret scan is Planned. |
| NFR-SEC-002 | Any non-localhost deployment of MongoDB or the vector DB shall require authentication and TLS. | Planned. Current state: Mongo in Docker, no auth, localhost only (accepted for local-first). |
| NFR-SEC-003 | The UI and API shall use authenticated sessions or tokens, role-based access (user, admin), CSRF protection for forms, and per-user rate limits. | Planned. |
| NFR-SEC-004 | Third-party credentials (GitHub tokens, OAuth) shall be stored encrypted at rest, scoped to read-only, and revocable. | Planned. |
| NFR-SEC-005 | The crawler browser profile shall be dedicated to the crawler (never the everyday profile) and shall not be committed. | **Implemented** (`user_data_dir: ~/.config/digital-twin-chrome`; Chrome refuses the default profile and the code explains why). |
| NFR-SEC-006 | Ingested content shall be treated as untrusted. Retrieved text shall not be able to change system instructions (prompt-injection defences in RAG). | Planned. Injection test cases in EVAL-005. |
| NFR-SEC-007 | Dependencies shall be pinned (`uv.lock`) and scanned for known vulnerabilities in CI. | Lockfile **Implemented**. Scan Planned. |

### 3.5 Privacy (PRIV)
| ID | Requirement | Measure / status |
|---|---|---|
| NFR-PRIV-001 | Raw data, datasets and models containing personal content shall stay private: local or private remotes only, never in the public git repo. | **Implemented** for raw data (DVC remote on a local drive; git holds only pointers). Datasets and models: Planned. |
| NFR-PRIV-002 | The public repository shall not expose personal paths or private identifiers beyond what the owner accepts. | **Open**: `configs/users/omar/sources/obsidian.yaml` holds an absolute home path, and comments name an employer test. See OQ-07. |
| NFR-PRIV-003 | Data minimisation: only content needed for style or knowledge is ingested. Sensitive folders are excludable. | **Partial** (glob excludes). Frontmatter opt-out is Planned (FR-OBS-004). |
| NFR-PRIV-004 | Inference traces shall be retained for a bounded period (default 90 days) and then deleted or anonymised. | Planned. |

### 3.6 Maintainability (MNT)
| ID | Requirement | Measure / status |
|---|---|---|
| NFR-MNT-001 | Code organisation: one package per provider, pure helpers in `utils/`, settings in `settings/`, one exception hierarchy rooted at `DigitalTwinError`. Adding a source type means adding one spec module, one registry entry and the extractor handling. | **Implemented**. |
| NFR-MNT-002 | Automated tests: unit tests for pure functions (keys, globs, parsers, topic matcher, markdown cleaners); contract tests for each extractor with recorded fixtures (no network); store tests against an ephemeral Mongo. | Planned. Target ≥ 70% line coverage on `llm_engineering/` excluding infrastructure adapters. There is currently no `tests/` directory. |
| NFR-MNT-003 | Static checks (ruff, mypy) shall pass with zero errors on `main`. | Caches suggest these are run locally, but they are not enforced. Planned in CI. |
| NFR-MNT-004 | Documentation: the README covers setup, running, configuration and architecture. Each pipeline has a docstring describing its inputs and outputs. | Docstrings: **Implemented**. `README.md` is **empty (0 bytes)**, so Planned. |
| NFR-MNT-005 | Python 3.12+, dependency management with `uv`, ZenML pinned (`0.96.3`). | **Implemented**. |

### 3.7 Observability (OBSV)
| ID | Requirement | Measure / status |
|---|---|---|
| NFR-OBSV-001 | Every pipeline run shall be identifiable (`run_id`) and traceable from a stored document back to the run that last saw it. | **Implemented** (run name, `provenance.run_id`, `sources.state.last_run_id`). |
| NFR-OBSV-002 | Each ETL run shall show a per-provider, per-source, per-item report with outcome reasons. | **Implemented** (HTML report artifact). |
| NFR-OBSV-003 | Logs shall be structured: level, provider, source id, run id. | **Partial** (standard logging with provider and source in messages; not structured). |
| NFR-OBSV-004 | Metrics shall be exported over time: documents per provider and topic, failure rate per source, crawl duration, and (later) inference latency, cost and quality. | Planned. |

### 3.8 Compliance and ethics (CMP)
| ID | Requirement | Measure / status |
|---|---|---|
| NFR-CMP-001 | Only official, terms-permitted channels shall be used for content: RSS feeds, official REST APIs, user-initiated data exports, local files, and public pages that do not forbid crawling. | **Implemented** for Medium text (RSS), GitHub (API) and LinkedIn (export). See RISK-01 for Medium tag discovery. |
| NFR-CMP-002 | No paywall, login-wall, CAPTCHA or bot-detection circumvention. A bot challenge that does not clear on its own shall stop that provider (`AccessBlockedError`), not be retried with evasion techniques. | **Implemented** in behaviour: the browser waits for an interstitial and then raises. Member-only content is skipped. See RISK-01. |
| NFR-CMP-003 | Polite crawling: identifying User-Agent, minimum delays, backoff on 429 and 5xx, honouring `Retry-After`, and robots.txt for generic pages. | **Partial**: delays and backoff are implemented. robots.txt is Planned (FR-ART-003). The browser uses a stock UA. |
| NFR-CMP-004 | External content shall keep attribution (author, url) and shall not be redistributed. Raw external text shall not appear in any public artifact (repo, public dataset, public model card). | Attribution fields: **Implemented**. Non-redistribution checks: Planned. |
| NFR-CMP-005 | Model and dataset licences shall be compatible with the base model's licence and the project's proprietary licence. The licence of each training-data source shall be recorded. | Planned. |
| NFR-CMP-006 | Data of users other than the owner shall be processed only with their explicit consent, recorded at registration (terms acceptance and timestamp). | Planned. |

---

## 4. Constraints and assumptions

### 4.1 Constraints
- C1: **Local-first.** MongoDB runs in Docker on localhost. The DVC remote is a local drive (`/run/media/omar/My Passport1/dvc-remotes/DigitalTwin`). ZenML uses its local server.
- C2: **Stack decisions already made:** Python 3.12, uv, Pydantic v2 and pydantic-settings, MongoDB, ZenML 0.96.3, DVC, Selenium (Chromium) for Medium tag discovery only, LangChain loaders for articles and Obsidian.
- C3: **Proprietary licence** (`LICENSE`, classifier `Private :: Do Not Upload`), while the GitHub repository is public.
- C4: **Single operator with limited budget.** Training compute and LLM API spend must be capped (FR-DS-007, FR-FT-006).
- C5: **Platform limits:** Medium feeds carry only about the latest 10 posts per feed. GitHub allows 60 req/h without a token and 5000 req/h with one. LinkedIn content comes only via a manual export, with platform-defined latency.
- C6: **Medium tag discovery needs a headed browser with a dedicated profile.** It cannot run unattended on a headless server without falling back to RSS.
- C7: **The Obsidian vault is on the owner's machine.** Obsidian ingestion cannot run elsewhere without a sync mechanism.

### 4.2 Assumptions
- A1: The owner's GitHub repositories, Obsidian notes and LinkedIn posts are predominantly the owner's own writing.
- A2: Free Medium posts delivered in full through official RSS may be read and stored privately for personal retrieval. See OQ-03 on training use.
- A3: About 100 external items per topic is enough knowledge coverage for RAG in the first iteration.
- A4: Future users are few (≤ 50) and known to the owner.
- A5: An open-weight base model of about 8B parameters fine-tuned with LoRA can capture style on the owner's hardware or affordable cloud GPUs.

---

## 5. Data requirements

### 5.1 Entities (current: Implemented)

**User** (`users`): `_id` (pattern `^[a-z0-9][a-z0-9_-]*$`), `name` (author of own documents), `handles{platform→handle}`.

**Source** (`sources`): `_id` (canonical key, for example `medium:tag:rag`, `medium:author:@x`, `github:user:x`, `obsidian:<user>:<abs path>`, `linkedin:<user>`, `article:<normalised url>`), `type`, `provider`, `spec` (declared JSON), `owner_id?`, `topics[]`, `enabled`, `state{status, last_run_id, last_crawled_at, error, items_ok, items_failed, items_skipped}`.

**Subscription** (`subscriptions`): `user_id`, `source_id`, `created_at`. Logical id `user|source`, unique index on the pair.

**RawDocument** (`raw_documents`): see FR-ETL-004. Ids: `medium:<article_id>`, `github:<owner/repo>/<path>`, `obsidian:<user>:<rel path>`, `article:<short hash of source id>`, `linkedin_*` by export item. `source` kind ∈ {medium, linkedin_post, linkedin_article, linkedin_comment, obsidian, github, article}. `origin` ∈ {self, external}.

**Provenance**: `source_id`, `query`, `rank?`, `run_id`, `collected_at`.

**Topic** (YAML): key, `description`, `medium_tags[]`, `obsidian_tags[]` (31 topics).

**Snapshot** (DVC): `data/raw/<provider>.jsonl` and `data/raw/registry/{users,sources,subscriptions}.jsonl`. Identified by `data_md5` and the git commit.

### 5.2 Entities (planned)
| Entity | Key fields |
|---|---|
| CleanedDocument | `id` (= raw id), `owner_id`, `origin`, `kind`, `topics`, `content`, `raw_content_hash`, `cleaner_version`, `deleted_at?` |
| Chunk / vector point | `point_id` (hash of doc id and index), `document_id`, `chunk_index`, `text`, `embedding`, `embedding_model`, `owner_id`, `origin`, `topics`, `kind`, `url`, `title` |
| InstructionSample | `id`, `owner_id`, `instruction`, `answer`, `source_document_ids[]`, `origin`, `generator_model`, `prompt_version`, `split` |
| PreferenceSample | `id`, `owner_id`, `prompt`, `chosen`, `rejected`, `source_document_ids[]`, `generator_model`, `split` |
| DatasetVersion | `name`, `version`, `kind` (instruction/preference), `raw_snapshot_md5`, `counts`, `card` |
| ModelVersion | `id`, `owner_id`, `base_model@rev`, `stage` (sft/dpo), `parent_id?`, `dataset_versions[]`, `hyperparams`, `eval_report_id`, `tags` (staging/production) |
| EvalReport | `model_id`, `suite`, `metrics{}`, `thresholds{}`, `passed` |
| Trace | `trace_id`, `user_id`, `query`, `retrieved_chunk_ids[]`, `prompt_version`, `model_version`, `latency_ms{}`, `tokens`, `cost`, `feedback?` |
| TriggerEvent | `id`, `source_id`, `kind` (schedule/webhook/poll/watch/manual), `received_at`, `coalesced_into_run?`, `status` |
| Credential | `user_id`, `provider`, `encrypted_secret`, `scopes`, `created_at`, `revoked_at?` |
| Consent | `user_id`, `terms_version`, `accepted_at` |

### 5.3 Data quality rules
- DQ-1: `content` is non-empty and at least the source's `min_chars` (enforced per provider today).
- DQ-2: `content_hash` = sha256(content) for every document (Implemented).
- DQ-3: Every `topics` entry is a key in `topics.yaml` (enforced at config load for declared topics; mapped topics come from `topics.yaml` by construction).
- DQ-4: `owner_id` is set if and only if `origin=self` for owned sources. The exception is `article` with `origin=self`, which today has no owner (gap: ArticleSpec `owned=False`, so an owner's own blog post loses `owner_id`). Tracked as **OQ-08**.

### 5.4 Current volumes (baseline)
About 2,560 documents: GitHub 1190, Obsidian 1017, Medium 343, Articles 12, LinkedIn 0 (export pending). 31 topics. Medium cap 100 per topic.

---

## 6. External interfaces

| Interface | Direction | Protocol / format | Notes |
|---|---|---|---|
| Medium RSS (`medium.com/feed/@author`, `/feed/<publication>`, `/feed/tag/<tag>`) | In | HTTPS, RSS/XML | Official. Paced at 3 s, with retries. |
| Medium tag pages (`/tag/<t>/recommended`) | In | Browser (Selenium, Chromium) | Link discovery only. Falls back to RSS when blocked. See RISK-01. |
| GitHub REST API v3 | In | HTTPS JSON, optional bearer token | Endpoints: repos, git trees, raw content. |
| LinkedIn data export | In | Files (CSV, HTML) in `data/exports/linkedin/<user>` | Git-ignored. Downloaded manually. |
| Obsidian vault | In | Local filesystem (markdown, PDF) | |
| Arbitrary web pages | In | HTTPS HTML → markdown | No JavaScript. 1 req/s. |
| MongoDB | In/Out | `mongodb://` or `mongodb+srv://` | Collections `users`, `sources`, `subscriptions`, `raw_documents`. |
| DVC remote | Out | DVC (local path today) | |
| Git | Out | Local commits of snapshot pointers | Pushing to GitHub is not automated. |
| ZenML server and dashboard | Out | ZenML API | Run tracking, HTML report artifacts. |
| CLI | In | `tools.run`, `tools.validate_sources` | |
| *Planned:* Vector DB (Qdrant) | Out/In | gRPC/HTTP | |
| *Planned:* LLM APIs (dataset generation, judging) | Out | HTTPS | Cost-capped. Content is sent to a third party, see OQ-05. |
| *Planned:* Model hub / registry (for example HF Hub, private) | Out | HTTPS | |
| *Planned:* Training compute (local GPU or cloud job) | Out | Provider SDK | |
| *Planned:* REST API and UI | In | HTTPS JSON, OpenAPI | Auth required. |
| *Planned:* Webhooks (GitHub) | In | HTTPS, HMAC-signed | |
| *Planned:* Tracing (Opik) | Out | SDK | |

---

## 7. Risks

| ID | Risk | Likelihood / impact | Mitigation |
|---|---|---|---|
| RISK-01 | **Medium tag discovery may conflict with the "no bot-detection evasion" value and with Medium's terms.** The browser uses a logged-in persistent profile, randomised human-like pauses and mouse-wheel scrolling, and waits (headed) for a human to click a challenge. These read as evasion techniques even though article text comes only from RSS. | Medium / High (account ban, reputational) | Decide per OQ-01. The options are to drop browser discovery and use only tag RSS (already the fallback), or to document a justification and never pass challenges by hand in unattended runs. |
| RISK-02 | Training on third-party external content (Medium articles, PDFs of lecture notes and books) may breach copyright or licences. | Medium / High | FR-DS-006 default: external content is retrieval only. Record licences per source. |
| RISK-03 | Private material (diaries in a vault named `workDiaries`, a job-application test, colleagues' names) leaks into the training set or into answers to other people. | Medium / High | FR-OBS-004 opt-out flag, FR-FEA-008 PII scrubbing, EVAL-005 safety tests, per-user isolation. |
| RISK-04 | Style contamination: external content mislabelled as `self` (vendored code in repos, quoted text in notes, PDFs) makes the twin sound generic. | Medium / Medium | FR-ETL-005 (done for PDFs), FR-GH-006, a stylometric audit of the `self` corpus before dataset generation. |
| RISK-05 | No tests and no CI: regressions in parsers and keys stay silent, and a key-normalisation change could duplicate sources. | High / Medium | NFR-MNT-002 and FR-OPS-003 before the feature pipeline work starts. |
| RISK-06 | Full re-fetch each run (GitHub, Obsidian) costs rate limit and time, and blocks frequent triggers. | High / Medium | FR-REG-011 and FR-GH-005 change detection. |
| RISK-07 | Upstream deletions are never reflected (no tombstones), so the twin may use content the user deleted. | High / Medium | FR-ETL-010. |
| RISK-08 | Medium feeds hold only about 10 posts, so tag coverage is limited and the corpus may skew towards recent posts. | High / Low | Accept, or add other sources per topic. Track topic counts against the cap in the summary (implemented). |
| RISK-09 | Concurrent runs (cron plus a manual or triggered run) collide on the browser profile or produce interleaved snapshots and commits. | Medium / Medium | FR-ORC-006 locking. |
| RISK-10 | A public repo with a proprietary licence and personal config is a confusing legal position and exposes personal data. | Medium / Medium | OQ-07. |
| RISK-11 | Dataset generation sends personal content to a third-party LLM API. | Medium / Medium | OQ-05. Prefer local models or providers with no-retention terms. |
| RISK-12 | An immutable DVC history conflicts with deletion requests (right to erasure) for future users. | Low now, rising with multi-user / High | OQ-06. Keep per-user data out of shared snapshots, or support rewriting snapshots. |

---

## 8. Open questions

| ID | Question | Why it matters / blocking |
|---|---|---|
| OQ-01 | Keep browser-based Medium tag discovery (logged-in profile, human pacing, manual challenge clicks), or switch to RSS-only discovery? | Compliance with the stated values (NFR-CMP-002) and the unattended triggers (C6). Blocks FR-TRG-002 for Medium. |
| OQ-02 | Which base model, which licence, and what compute budget for SFT/DPO? | Drives FT, the size of the dataset to generate, and inference hosting. |
| OQ-03 | May external content (Medium free posts, PDFs, articles) be used for training, or only for retrieval? | FR-DS-006, RISK-02. |
| OQ-04 | Vector DB and embedding model choice (Qdrant? local vs hosted embeddings?), and should cleaned documents live in Mongo or only in vector payloads? | Blocks the FEA design. |
| OQ-05 | Which LLM may see personal content during dataset generation and judging (local only, or an API with no retention)? | Privacy, and the cost of the DS and EVAL stages. |
| OQ-06 | How to honour deletion for multiple users given immutable git and DVC history? | FR-PRV-002, RISK-12. |
| OQ-07 | Should the repo stay public? If yes, move personal paths and identifiers out of `configs/users/omar/` (for example to a private overlay) and reconcile with the proprietary licence. | NFR-PRIV-002. |
| OQ-08 | Should an `article` with `origin=self` (the owner's own blog post) get `owner_id`? Today `ArticleSpec.owned=False`, so it does not. | Correctness of the self/external split (DQ-4). |
| OQ-09 | Where will a multi-user deployment run (owner's machine vs cloud), and how do remote users provide Obsidian vaults? | FR-OBS-005, FR-UI-005, NFR-SEC-002. |
| OQ-10 | Who are the twin consumers (only the owner, or recruiters and public)? Is a public-facing twin in scope? | FR-INF-005/006, safety evaluation scope. |
| OQ-11 | Should LinkedIn comments (replies to other people's posts) count as style data, given they lack context and include others' content? | Dataset quality and privacy. |
| OQ-12 | What target per-topic volume and freshness does RAG need, and should the 100-per-topic cap apply to providers other than Medium? | FR-ETL-008 scope. |
