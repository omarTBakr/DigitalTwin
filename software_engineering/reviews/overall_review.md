# DigitalTwin: Overall Review of the Software Engineering Artifacts

| | |
|---|---|
| Date | 2026-10-23 |
| Baseline | `main` at `4c40ca7` |
| Scope | Everything in `software_engineering/`: requirements, user stories, class diagram, sequence diagrams, and the reviews behind them |

## 1. How the artifacts were produced

| Step | Author | Output |
|---|---|---|
| 1 | Requirements agent | [`requirements_draft.md`](requirements_draft.md) (129 FR, 40 NFR) |
| 2 | Review agent (critique and enhance) | [`requirements_review.md`](requirements_review.md) (43 findings), [`requirements.md`](../requirements/requirements.md) v1.0 (161 FR + 1 withdrawn, 44 NFR, priorities, phases P0–P4, traceability) |
| 3 | Main session | [`user_stories.md`](../user_stories/user_stories.md) (96 stories in 13 epics, sprints S0–S16) |
| 4 | Class-diagram agent | [`class_diagram_draft.md`](class_diagram_draft.md) (17 diagrams; 121 implemented and 235 planned classes) |
| 5 | Review agent (critique and enhance) | [`class_diagram_review.md`](class_diagram_review.md) (45 findings), [`class_diagram.md`](../class_diagrams/README.md) v1.0 (124 implemented, 198 planned) |
| 6 | Main session | this review, the fixes in section 3, then [`sequence_diagram.md`](../sequence_diagrams/README.md) (9 diagrams) |

The draft files are kept unchanged next to the final ones, so every change can be traced through the review files.

## 2. Cross-artifact checks (scripted, all passing)

| Check | Result |
|---|---|
| Every non-withdrawn FR is delivered by at least one user story | 161 / 161 |
| A story's priority equals the strongest priority of its FRs | 96 / 96 |
| A story's sprint falls in the phase of its FRs | 94 / 96. The two exceptions are intended: US-025 (FR-MED-003, built in P0, decision in P1) and US-030 (LinkedIn, built in P0, verification in P1) |
| Every requirement ID cited in the class diagram exists | 0 unknown IDs |
| Every P1–P4 *Must* FR has a class, attribute or method home | All but FR-OPS-003 (CI). CI is a workflow, not a class; accepted |
| Every name used in the sequence diagrams exists in the code or in [`class_diagram.md`](../class_diagrams/README.md) | Checked by hand for each participant and planned method. Three mismatches were fixed (section 3) |
| All Mermaid diagrams render | Class diagram 17/17 (checked by the review agent), sequence diagrams 9/9 (mermaid-cli 11.x) |

## 3. Fixes applied in this review

1. **[`requirements.md`](../requirements/requirements.md), NFR-PRIV-002.** Changed from Planned to Partial. Commit `4c40ca7` replaced the absolute vault path. The employer test name, the local path in `.dvc/config` and the un-ignored `.zen/` are still open.
2. **[`requirements.md`](../requirements/requirements.md), section 5.2.** Added the entities that the class-diagram review introduced, so the data model and the class model agree:
   - `Exclusion` and `Lock` are new entities.
   - `CostEntry.user_id` is added. Without it, per-user caps can't be computed.
   - `SourceState` gains its extended fields (cursor, `last_success_at`, `retry_not_before`).
   - `RawDocument` gains its planned fields (`deleted_at`, `changed_at`, `schema_version`, `topics_by_source`).
3. **[`user_stories.md`](../user_stories/user_stories.md).** FR-ORC-005 (later stages run as separate ZenML pipelines) had no story. It is now part of US-059. The status counts were also corrected.
4. **[`sequence_diagram.md`](../sequence_diagrams/README.md).** Fixed while drafting:
   - It now uses `RunRecordStore.save` / `save_change_set` / `get_change_set`, the names in the class diagram.
   - `SnapshotLayout` is no longer shown as `Purgeable`, because it isn't.
   - A semicolon that broke Mermaid parsing was removed.

## 4. Critique of the work as a whole

### What is strong
- **The implemented part is grounded in the code.** The two review passes and the class-diagram reviewer checked more than 60 classes member by member. Every gap statement in the requirements was confirmed against real code, for example the `$set` of `owner_id`, `RateLimitError` being swallowed in `_find_in_feed`, and the copied Chrome User-Agent. Nothing claims behaviour the code lacks.
- **Traceability is end to end:** goal → FR → story → class → sequence step. A change to one requirement can be followed into every artifact.
- **Each cross-cutting rule has one owner:**
  - ownership: `RegistryStore.upsert_source`
  - visibility: `OwnerScope`
  - dataset admission: `TrainingDataSelector`
  - spend: `BudgetGuard`
  - backoff: `BackoffGate`
  - deletion: `Purgeable`

  That makes the privacy and cost requirements testable in one place each.
- **The reviews made real corrections, not cosmetic ones.**
  - The requirements review found the GitHub ownership takeover, the provider-wide crash on unexpected exceptions, and a tombstone rule that would have deleted every Medium article dropping out of a 10-item feed.
  - The class-diagram review removed three invented modules, broke two package cycles, and replaced a racy read-then-write ownership check with an atomic update.

### Weaknesses and risks in the artifacts

1. **Scale vs. a one-person project.** The artifacts plan 161 requirements, 96 stories and 198 planned classes. The P1 design is concrete and should be built as drawn. P2–P4 depend on open questions (OQ-02 base model, OQ-03 training on external content, OQ-04 vector DB, OQ-05 which LLM sees personal data, OQ-14 auth), so their classes and sequences are a target architecture, not a commitment. Re-run the design step (class diagram plus sequence diagrams for that phase) at the start of P2, P3 and P4, and expect merges.
2. **Technology is picked ahead of decisions.** The planned design names Qdrant, Opik, a cross-encoder reranker, an 8B LoRA model and a private Hugging Face Hub. These are reasonable defaults but are still open questions in the requirements. The class diagram isolates them behind ABCs (`VectorStore`, `Tracer`, `ComputeBackend`, `DatasetStore`), which keeps the cost of changing them low.
3. **The sprint numbers past S4 are placeholders.** There is no velocity data yet, and stories differ a lot in size (US-013 and US-016 bundle 2–3 FRs each, US-019 is nearly done). Re-estimate after Sprint 1 and split the large stories during sprint planning.
4. **The same facts appear in several documents.** The baseline commit, statuses and entity fields are repeated across four files, and they had already drifted (fix 1 and fix 2 above). Rule from now on: [`requirements.md`](../requirements/requirements.md) owns status, priority and phase; the other documents cite IDs and do not restate them.
5. **Several NFR targets are guesses.** Examples: p95 ≤ 5 s, ≤ 3 h for a full ETL, ≥ 70% test coverage. No measurement exists yet. NFR-PERF-001 should be measured on the next full run (the last full Medium run took 19 minutes) and the targets set from that.
6. **"Implemented" means "read in the code", not "tested".** There is no `tests/` directory. Until NFR-MNT-002 and FR-OPS-003 are done, every Implemented status is only as good as the reviewers' reading.

## 5. Decisions needed from the owner before Sprint 1 ends

| ID | Decision | Recommendation |
|---|---|---|
| OQ-01 | Medium tag discovery: browser or RSS only | RSS only for every unattended run. Remove the browser path or keep it as an interactive opt-in where no person solves a challenge. Scheduled Medium runs (FR-TRG-002) are blocked until this is decided. |
| OQ-07 | Public repo with personal configuration | Move `configs/users/omar/` to a private overlay (git-ignored, with an example folder committed), or make the repo private. The proprietary licence and a public repo are an odd pair either way. |
| OQ-13 | Monthly budgets | Needed before P2 (embeddings) and P3 (generation, GPU). |
| — | Sign-off on the P1 *Must* list | See [`requirements_review.md`](requirements_review.md). |

## 6. Sprint 1 quick wins collected from all reviews

These are small, concrete code fixes found while producing the artifacts:

1. **Ownership.** Remove `owner_id` from `DECLARATION_FIELDS`. Set it with `$setOnInsert` and reject an owner change (FR-REG-012). This closes the GitHub takeover.
2. **Unexpected exceptions.** Catch them per source in `BaseExtractor.extract` and in `crawl_provider`, so one extractor bug doesn't stop the run (FR-ETL-012).
3. **Medium rate limits.** Let `RateLimitError` propagate out of `_find_in_feed`, raise `SourceUnavailableError` for exhausted 5xx, and honour `Retry-After` (FR-MED-005).
4. **Article crawler User-Agent.** Replace the copied Chrome string with `DigitalTwinCrawler/0.1 (+https://github.com/omarTBakr/DigitalTwin)`. Add the contact URL to the Medium and GitHub clients too (FR-ART-002).
5. **Dead setting.** Remove the never-read `MediumSettings.skip_member_only` (FR-CFG-005).
6. **Name clash.** Rename the token class in `settings/app_settings.py` to `GitHubApiSettings`.
7. **Stale docs and comments.** Fix the "(Selenium)" in the `crawl_medium` docstring and the "opens Medium in Chrome" in the `validate_sources` docstring. Fix the "needed for private repos" claim in `.env.example`.
8. **Stray files.** Add `.zen/` to `.gitignore`. Write `README.md`.
9. **Undeclared extractor attributes.** Declare the attributes that `session()` sets (`client`, `feeds`, `listing`, …) in `__init__`, so mypy can check them.
