# DigitalTwin: User Stories Backlog

Derived from [`requirements.md`](../requirements/requirements.md) v1.0 (baseline `main` at `264cc1c`). Each story traces to the functional
requirements (FR) it delivers; the trace table follows the backlog.

**Roles:** *Owner* (Omar: operator, developer, first user) · *User* (an invited, authenticated future user) ·
*Admin* (initially the owner) · *Twin consumer* (someone chatting with a twin) · *Scheduler* (system actor).

**Priority:** MoSCoW from the requirements (Must / Should / Could).
**Sprint:** two-week sprints. Sprint 0 is the ETL already built (phase P0). Phase → sprints:
P1 ETL hardening and triggers = S1–S4 · P2 feature pipeline and RAG = S5–S8 · P3 datasets, fine-tuning, evaluation = S9–S12 · P4 UI, multi-user and LLMOps = S13–S16.
**Status:** *Done* (all linked FRs Implemented) · *Partially done* (some linked FRs Implemented or Partial) · *On hold* (built, awaiting an owner decision) · *To do* (nothing built).

## Backlog

| ID | As a… | I want to be able to… | So that… | Priority | Sprint | Status |
|---|---|---|---|---|---|---|
| **Epic E1: Configuration and topics** | | | | | | |
| US-001 | Owner | define my topics once in `topics.yaml` and map each to Medium tags and Obsidian tags | every source and document is labelled with the same topic vocabulary | Must | S0 | Done |
| US-002 | Owner | declare my profile and sources in per-user YAML files that are validated before anything is crawled | a typo or unknown field fails fast with a clear message instead of a half-finished run | Must | S0 | Done |
| US-003 | Owner | keep secrets and connection settings in one `.env`-backed settings object | credentials never live in code or YAML and are masked in logs | Must | S0 | Done |
| US-004 | Owner | tune each provider (delays, caps, retries) in its own config file, with every setting actually honoured | I can change crawler behaviour without touching code, and no setting is a dead switch | Should | S1 | Partially done |
| US-005 | Owner | run a health check that validates all config and probes each provider, also offline | I know a run will work before I start it | Should | S0 | Done |
| US-006 | Owner | rename or retire a topic and have stored documents migrated or flagged | topic labels stay consistent with the data they describe | Should | S5 | To do |
| **Epic E2: Source registry and multi-user** | | | | | | |
| US-007 | Owner | have every source stored once under a canonical key, whoever declares it and however it is spelled | the same tag, author or URL is never crawled or stored twice | Must | S0 | Done |
| US-008 | Owner | see each source's latest crawl state (status, last run, error, item counts) in the registry | I can tell which sources are healthy without opening logs | Must | S0 | Done |
| US-009 | Owner | run the ETL for everything, for one user, or for specific source ids, and be told when a requested source is disabled | triggers and manual runs crawl exactly what I asked, with no silent drops | Should | S1 | Partially done |
| US-010 | Owner | remove a source or unsubscribe and have the registry reflect it | removed sources stop being crawled and don't linger as stale records | Should | S2 | To do |
| US-011 | Owner | have an owned source (e.g. my GitHub account) keep exactly one owner, rejecting any conflicting claim | nobody else can claim my code as their own writing | Must | S1 | To do |
| US-012 | User | subscribe to a shared source that other users already follow, with topics and enabled flags merged fairly | my choices don't overwrite or get overwritten by other subscribers | Must | S2 | To do |
| US-013 | Owner | have unchanged content skipped on re-runs using each platform's change signals, with the crawl state keeping cursors, last success and retry-after times | frequent triggered runs are cheap, polite, and don't rewrite identical data | Must | S2 | Partially done |
| US-014 | User | have my own content isolated from every other user's twin | my notes and code are never retrieved or trained into someone else's twin | Must | S6 | Partially done |
| **Epic E3: Extraction framework** | | | | | | |
| US-015 | Owner | add a new data source by implementing one extractor contract | the system grows without changing the pipeline | Must | S0 | Done |
| US-016 | Owner | have failures isolated per item, per source and per provider, including unexpected bugs | one broken item, source or extractor never stops the rest of the run or loses collected data | Must | S1 | Partially done |
| US-017 | Owner | see a per-source, per-item crawl report (ok / failed / skipped with a reason) in the ZenML dashboard | I can audit exactly what was collected and why something was skipped | Must | S0 | Done |
| US-018 | Owner | have every document follow one schema with provenance (source, query, rank, run, time) and a self/external origin | downstream stages can trust, trace and filter every record | Must | S0 | Done |
| US-019 | Owner | cap each topic at about 100 items across runs | the corpus stays balanced across topics | Should | S0 | Done |
| US-020 | Owner | have content deleted upstream marked as deleted (only when the source was fully listed) | the twin never answers from notes or repos I removed | Must | S2 | To do |
| US-021 | Owner | have topics recomputed when I fix a rule or mapping, so wrong topics are removed | topic labels stay correct as the configuration evolves | Should | S3 | To do |
| US-022 | Owner | detect exact and near-duplicate documents reachable under different ids | duplicates don't skew retrieval or training | Should | S5 | To do |
| **Epic E4: Providers** | | | | | | |
| US-023 | Owner | collect Medium articles for my topics and followed authors from official RSS feeds only, skipping member-only stories | I get high-quality external knowledge without scraping or bypassing the paywall | Must | S0 | Done |
| US-024 | Scheduler | run Medium discovery fully unattended (RSS only, no browser, no human clicks), backing off correctly on rate limits | scheduled runs work on a headless machine and stay within Medium's terms | Must | S1 | Partially done |
| US-025 | Owner | discover a tag's top articles with a browser only in interactive mode, falling back to RSS when challenged | I keep better discovery when I'm present without needing to solve bot checks | Could | S1 | On hold |
| US-026 | Owner | ingest my own Medium posts as my writing | my published articles teach the twin my style | Could | S3 | To do |
| US-027 | Owner | ingest markdown, Python and notebooks from my public GitHub repos with filters | my code and documentation become part of the twin's knowledge and voice | Must | S0 | Done |
| US-028 | Owner | skip unchanged GitHub repos and files, record truncated trees, and exclude vendored code | GitHub runs are fast and only my own code counts as mine | Must | S2 | Partially done |
| US-029 | Owner | optionally include my private repositories with a token | private projects can inform my twin when I choose | Could | S15 | To do |
| US-030 | Owner | ingest my LinkedIn posts, articles and comments from the official data export | my professional writing is included without scraping LinkedIn | Must | S1 | Partially done |
| US-031 | User | upload my LinkedIn export zip in the UI and have it ingested automatically | I don't need shell access to add my LinkedIn content | Should | S14 | To do |
| US-032 | Owner | ingest my Obsidian vault (notes and selected PDFs) with include/exclude rules | my personal knowledge base becomes the twin's core | Must | S0 | Done |
| US-033 | Owner | mark notes private by frontmatter flag and have one unreadable note fail only itself | sensitive notes stay out and one bad file doesn't fail the whole vault | Must | S2 | Partially done |
| US-034 | User | sync or upload my vault when the system doesn't run on my machine | remote and multi-user setups can include Obsidian | Should | S15 | To do |
| US-035 | Owner | ingest web articles by URL, politely (identifying user agent, robots.txt, pacing) | individual great articles can be added within each site's rules | Must | S1 | Partially done |
| US-036 | Owner | mark an article as my own blog post and extract real bylines | my posts count as my writing and external authors are attributed properly | Should | S3 | Partially done |
| **Epic E5: Storage, orchestration and versioning** | | | | | | |
| US-037 | Owner | store raw documents behind a swappable store with idempotent upserts and indexes | re-runs never duplicate data and I can change the backend later | Must | S0 | Done |
| US-038 | Owner | have changed and deleted documents flagged, purgeable and schema-versioned in the store | downstream stages know exactly what changed and old records stay readable | Must | S2 | To do |
| US-039 | Owner | run the whole ETL as a ZenML pipeline or from the CLI, with per-provider summaries | I can operate and monitor collection from one place | Must | S0 | Done |
| US-040 | Owner | have the run fail clearly at the end if any provider failed, while keeping all collected data | failures are visible without losing successful work | Must | S1 | Partially done |
| US-041 | Owner | prevent two runs from crawling the same source or writing snapshots at the same time | triggers and manual runs never collide | Must | S3 | To do |
| US-042 | Owner | get a run record (trigger, selection, code commit, config hash, summaries, snapshot) and a change set per run | every run is reproducible and the feature pipeline knows what to process | Must | S3 | To do |
| US-043 | Owner | snapshot the raw data with DVC after each run (deterministic export, commit, push) | every dataset and model can be traced to an exact data version | Must | S0 | Done |
| US-044 | Owner | have snapshot commits pushed before committing, kept off my working branch, and restorable into an empty database | snapshots are always fetchable and I can rebuild the store from any version | Should | S3 | To do |
| US-045 | User | have my data stored in its own snapshot partition | deleting my account doesn't require rewriting other users' data | Should | S16 | To do |
| **Epic E6: Triggers and scheduling** | | | | | | |
| US-046 | Scheduler | run each provider on its configured cadence, unattended | the twin stays current without me starting runs | Must | S4 | To do |
| US-047 | Owner | have a new GitHub push, Medium post or vault edit trigger ingestion of only that source, debounced | my latest work reaches the twin within minutes, without a full run | Should | S4 | To do |
| US-048 | Scheduler | respect rate-limit and blocked-access cool-downs, log every trigger event and retry failed triggered runs a bounded number of times | triggers stay polite and failures are visible and recoverable | Must | S4 | To do |
| US-049 | Owner | have a non-empty ETL change set automatically trigger the feature pipeline for just those documents | new content becomes searchable without manual steps | Must | S8 | To do |
| US-050 | Owner | receive platform webhooks that are signature-verified and replay-protected | event triggers can be instant without opening a security hole | Must | S16 | To do |
| **Epic E7: Source registration UI and API** | | | | | | |
| US-051 | User | sign in with an invite-only account, with roles and session expiry, after accepting the terms | only invited people can use the system and my consent is recorded | Must | S13 | To do |
| US-052 | User | add a source through a validated form, and be subscribed instead of duplicating an existing source | I can register what I want ingested without YAML, and nothing is crawled twice | Must | S13 | To do |
| US-053 | User | see my subscriptions with their crawl status, last success and errors | I know whether my data is up to date | Must | S14 | To do |
| US-054 | User | trigger an on-demand crawl of my own sources, within a rate limit and my quotas | I can refresh my twin now without overloading the system | Should | S14 | To do |
| US-055 | User | connect GitHub with OAuth (proving the account is mine) and manage credentials I can revoke | my own-content sources are verified and my tokens stay under my control | Must | S14 | To do |
| US-056 | User | exclude specific sources or documents from training and/or retrieval and see what my twin was trained on | I stay in control of what my twin knows | Must | S15 | To do |
| US-057 | Admin | manage users, topics, provider settings, quotas and globally disabled sources | the platform stays healthy and fair as users join | Should | S15 | To do |
| US-058 | Owner | have every UI action available through a versioned REST API with an OpenAPI schema, and have UI-made records never overwritten by YAML sync | integrations and the UI share one contract and UI edits are safe | Must | S13 | To do |
| **Epic E8: Feature pipeline** | | | | | | |
| US-059 | Owner | clean raw documents with versioned per-kind rules in their own ZenML pipeline, and quarantine low-quality content | only clean, meaningful text reaches the index and datasets | Must | S5 | To do |
| US-060 | Owner | chunk documents by kind (headings, code structure, whole posts) and embed them with a recorded model | retrieval returns coherent passages and embeddings are never mixed across models | Must | S6 | To do |
| US-061 | Owner | store vectors with filterable metadata (owner, origin, topic, kind, deleted) | retrieval can be scoped to a user and to self or external content | Must | S6 | To do |
| US-062 | Owner | update the index incrementally and idempotently, deleting vectors of removed or excluded documents | the index stays exact without full rebuilds | Must | S7 | To do |
| US-063 | Owner | have secrets masked before indexing and PII masked before training | private keys and personal data never leak through the twin | Must | S7 | To do |
| US-064 | Owner | bound embedding cost with a local default model and a cap for hosted models | re-embedding never causes a surprise bill | Should | S7 | To do |
| US-065 | Owner | re-index into a new collection and switch an alias when complete | queries never hit a half-built index | Could | S8 | To do |
| US-066 | Owner | "forget" a document or path with one command | something I regret ingesting disappears from search and future training | Should | S8 | To do |
| **Epic E9: RAG inference service** | | | | | | |
| US-067 | Twin consumer | ask the twin a question through an API and get an answer with cited sources and an AI disclosure | I can verify the answer and know it was generated by AI | Must | S7 | To do |
| US-068 | Twin consumer | get a "don't know" answer when nothing relevant is found, and never a citation to something not retrieved | the twin doesn't invent knowledge | Must | S7 | To do |
| US-069 | Owner | have retrieval use query rewriting, metadata filters scoped to the user, and reranking, each switchable | answers are relevant and I can measure each technique's effect | Should | S8 | To do |
| US-070 | Owner | protect the API with tokens, rate limits and a daily spend cap | the twin can't be abused or run up costs | Must | S7 | To do |
| US-071 | Twin consumer | receive streamed responses | answers feel responsive | Could | S8 | To do |
| US-072 | Twin consumer | get answers generated by the owner's fine-tuned model, with a base-model fallback | the twin sounds like its owner even if the adapter is unavailable | Must | S12 | To do |
| **Epic E10: Datasets and fine-tuning** | | | | | | |
| US-073 | Owner | generate an instruction dataset from my style-eligible writing, with cost caps | the model learns my voice from text that is actually mine | Must | S9 | To do |
| US-074 | Owner | generate a preference dataset (my voice vs. generic answers) | DPO can push the model toward my style | Should | S10 | To do |
| US-075 | Owner | filter, deduplicate and split datasets by source document, with minimum size and quality gates | training data is clean and evaluation isn't leaked | Must | S9 | To do |
| US-076 | Owner | use third-party content in training only when its licence allows (retrieval only by default), and get a dataset card per version | the twin respects authors' rights and every dataset is documented | Must | S9 | To do |
| US-077 | Owner | fine-tune an open-weight model with SFT then DPO on bounded, configurable compute | I get my own twin model within budget | Must | S10 | To do |
| US-078 | Owner | register every model with full lineage and reproduce a training run from recorded inputs | any model can be traced to its data and code and rebuilt | Must | S11 | To do |
| US-079 | User | have my own adapter trained only on my data and external content | my twin is mine alone | Must | S16 | To do |
| **Epic E11: Evaluation** | | | | | | |
| US-080 | Owner | keep an owner-approved evaluation set that is never used for training | quality is judged against answers I agree with | Must | S9 | To do |
| US-081 | Owner | evaluate RAG retrieval and generation on a curated question set per topic | I know whether retrieval changes improve answers | Must | S8 | To do |
| US-082 | Owner | evaluate candidate models on style, relevance, faithfulness and general capability, and promote only those that beat production | only better models reach the twin | Must | S11 | To do |
| US-083 | Owner | run safety checks (privacy refusal, prompt injection, AI disclosure) before promotion | the twin can't be tricked into leaking data or pretending to be human | Must | S12 | To do |
| **Epic E12: LLMOps** | | | | | | |
| US-084 | Owner | have CI run lint, type checks, tests, config validation and secret and dependency scans on every push | regressions and leaked secrets are caught before they reach `main` | Must | S1 | To do |
| US-085 | Owner | be alerted when a provider fails or a source fails several runs in a row | broken sources get fixed quickly | Should | S4 | To do |
| US-086 | Owner | back up Mongo and the vector DB on a schedule and test restores | a disk failure doesn't lose the twin's data | Should | S4 | To do |
| US-087 | Owner | trace every inference request with prompt version, retrieved chunks, model version, latency and cost | I can debug and improve answers | Should | S6 | To do |
| US-088 | Owner | meter all spend against monthly budgets with a hard stop | the project never exceeds what I'm willing to pay | Must | S5 | To do |
| US-089 | Owner | deploy the inference service as a container through staging and production with one-step rollback | releases are safe and reversible | Should | S15 | To do |
| US-090 | Owner | monitor errors, latency, cost, empty retrievals and quality drift in production | I notice degradation before users do | Should | S16 | To do |
| US-091 | Twin consumer | give thumbs up/down or corrections on answers | the twin can learn from feedback | Could | S16 | To do |
| **Epic E13: Privacy and data-subject operations** | | | | | | |
| US-092 | User | export all data held about me | I can see and take everything the system knows about me | Should | S16 | To do |
| US-093 | User | delete my account and have every trace of my data removed from all stores | leaving the platform really means leaving | Must | S16 | To do |
| US-094 | Owner | have third-party personal data in my notes replaced with placeholders before training | other people's names and contacts don't end up in my model | Must | S10 | To do |
| US-095 | Owner | have models trained on later-deleted data flagged and retrained or retired | deletions also reach the models | Must | S16 | To do |
| US-096 | Owner | decide whether a shared source's documents are kept or purged when its last subscriber leaves | orphaned external data follows a clear policy | Should | S2 | To do |

## Sprint plan summary

| Sprint | Phase | Goal | Stories |
|---|---|---|---|
| S0 | P0 | ETL as built | US-001–003, 005, 007, 008, 015, 017–019, 023, 027, 032, 037, 039, 043 |
| S1 | P1 | Safety net and compliance | US-004, 009, 011, 016, 024, 025 (decision), 030, 035, 040, 084 |
| S2 | P1 | Incremental crawl and deletions | US-010, 012, 013, 020, 028, 033, 038, 096 |
| S3 | P1 | Run integrity and lineage | US-021, 026, 036, 041, 042, 044 |
| S4 | P1 | Triggers and ops basics | US-046, 047, 048, 085, 086 |
| S5–S8 | P2 | Feature pipeline and RAG | US-006, 014, 022, 049, 059–071, 081, 087, 088 |
| S9–S12 | P3 | Datasets, fine-tuning, evaluation | US-072–078, 080, 082, 083, 094 |
| S13–S16 | P4 | UI, multi-user, LLMOps | US-029, 031, 034, 045, 050–058, 079, 089–093, 095 |

## Status summary

| Status | Count |
|---|---|
| Done | 16 |
| Partially done | 12 |
| On hold | 1 |
| To do | 67 |
| **Total** | **96** |

## Traceability: story → requirements

| Story | Functional requirements | Story | Functional requirements |
|---|---|---|---|
| US-001 | CFG-001 | US-049 | TRG-005 |
| US-002 | CFG-002, CFG-003 | US-050 | TRG-007 |
| US-003 | CFG-004 | US-051 | UI-009, UI-010 |
| US-004 | CFG-005 | US-052 | UI-001, UI-002 |
| US-005 | CFG-006 | US-053 | UI-003 |
| US-006 | CFG-007 | US-054 | UI-004, UI-012 |
| US-007 | REG-001, REG-002, REG-003, REG-004, REG-005 | US-055 | UI-005, UI-011 |
| US-008 | REG-006 | US-056 | UI-006 |
| US-009 | REG-007 | US-057 | UI-007, UI-012 |
| US-010 | REG-008, REG-009 | US-058 | UI-008, CFG-008 |
| US-011 | REG-012 | US-059 | FEA-001, FEA-006, FEA-007, ORC-005 |
| US-012 | REG-013 | US-060 | FEA-002, FEA-003 |
| US-013 | REG-011, REG-014 | US-061 | FEA-004 |
| US-014 | REG-010 | US-062 | FEA-005 |
| US-015 | ETL-001 | US-063 | FEA-008 |
| US-016 | ETL-002, ETL-009, ETL-012 | US-064 | FEA-009 |
| US-017 | ETL-003 | US-065 | FEA-010 |
| US-018 | ETL-004, ETL-005, ETL-006 | US-066 | PRV-006 |
| US-019 | ETL-007, ETL-008 | US-067 | INF-001, INF-006 |
| US-020 | ETL-010 | US-068 | INF-007 |
| US-021 | ETL-013 | US-069 | INF-002 |
| US-022 | ETL-011 | US-070 | INF-005, INF-008 |
| US-023 | MED-001, MED-002, MED-004, MED-006 | US-071 | INF-004 |
| US-024 | MED-005, MED-008 | US-072 | INF-003 |
| US-025 | MED-003 | US-073 | DS-001, DS-007, DS-008 |
| US-026 | MED-007 | US-074 | DS-002 |
| US-027 | GH-001, GH-002, GH-003 | US-075 | DS-003, DS-004, DS-010 |
| US-028 | GH-004, GH-005, GH-006 | US-076 | DS-005, DS-006, VER-005 |
| US-029 | GH-007 | US-077 | FT-001, FT-002, FT-006 |
| US-030 | LI-001, LI-002, LI-003 | US-078 | FT-003, FT-004, VER-004 |
| US-031 | LI-004 | US-079 | FT-005 |
| US-032 | OBS-001, OBS-002, OBS-003 | US-080 | DS-009 |
| US-033 | OBS-004, OBS-006 | US-081 | EVAL-003 |
| US-034 | OBS-005 | US-082 | EVAL-001, EVAL-002, EVAL-004 |
| US-035 | ART-001, ART-002, ART-003 | US-083 | EVAL-005 |
| US-036 | ART-004, ART-005 | US-084 | OPS-003 |
| US-037 | STO-001, STO-002, STO-003, STO-004 | US-085 | OPS-006 |
| US-038 | STO-005, STO-006, STO-007 | US-086 | OPS-009 |
| US-039 | ORC-001, ORC-002, ORC-003 | US-087 | OPS-001, OPS-002 |
| US-040 | ORC-004 | US-088 | OPS-008 |
| US-041 | ORC-006 | US-089 | OPS-004 |
| US-042 | ORC-007, ORC-008 | US-090 | OPS-005 |
| US-043 | VER-001, VER-002, VER-003 | US-091 | OPS-007 |
| US-044 | VER-006, VER-007 | US-092 | PRV-001 |
| US-045 | VER-008 | US-093 | PRV-002 |
| US-046 | TRG-002 | US-094 | PRV-004 |
| US-047 | TRG-003, TRG-004 | US-095 | PRV-005 |
| US-048 | TRG-006, TRG-008 | US-096 | PRV-003 |

FR-TRG-001 is withdrawn and has no story. Non-functional requirements are acceptance constraints on the stories
above (for example NFR-CMP-002 on US-024/025, NFR-MNT-002 on US-084) rather than stories of their own.
