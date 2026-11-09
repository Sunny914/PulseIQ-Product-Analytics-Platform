# PulseIQ — Development History & Implementation Log

This file is the **single source of truth** for PulseIQ development history.  
Append new workstream entries chronologically. Do not remove or rewrite completed history.

**Update policy:** At the end of every implementation task, add or update the relevant workstream section with verified implementation and validation results only.

---

## Phase 0 — Data Integrity & Reproducibility

---

### WS-1: Centralized DuckDB Configuration

**Status:** Completed

**Objective**  
Eliminate inconsistent DuckDB file paths across Bronze, Silver, Gold, and export scripts so all layers resolve one authoritative database regardless of working directory.

**Changes Implemented**

- Added `sql/db_config.py` with repository-root resolution via `pathlib` (not process CWD).
- Defined authoritative database file: `{REPO_ROOT}/product_analytics_light.db`.
- Added `get_repo_root()`, `get_db_path()`, and `connect_duckdb(read_only=...)`.
- Optional override via environment variable `PULSEIQ_DB_PATH`.
- Replaced per-script `duckdb.connect(...)` path logic with imports from `db_config`.
- Bronze/Silver scripts previously resolved `sql/product_analytics_light.db`; Gold/export already used repo root — all now align to repo root by default.

**Files Created**

- `sql/db_config.py`

**Files Modified**

- `sql/bronze/bronze_accounts.py`
- `sql/bronze/bronze_users.py`
- `sql/bronze/bronze_deals.py`
- `sql/bronze/bronze_product_events.py`
- `sql/bronze/bronze_geography.py`
- `sql/silver/silver_accounts.py`
- `sql/silver/silver_users.py`
- `sql/silver/silver_deals.py`
- `sql/silver/silver_product_events.py`
- `sql/silver/silver_geography.py`
- `sql/gold/gold_dim_accounts.py`
- `sql/gold/gold_dim_users.py`
- `sql/gold/gold_dim_geography.py`
- `sql/gold/gold_fact_deals.py`
- `sql/gold/gold_fact_product_events.py`
- `sql/gold/gold_fact_product_events_aggregated.py`
- `sql/gold/gold_fact_advanced_activation.py`
- `sql/gold/export_gold_to_csv.py`

*(Connection/bootstrap imports only; SQL transformation bodies unchanged.)*

**Technical Decisions**

- Central module lives under `sql/` because all transformation scripts already live in that tree.
- Layer scripts prepend `sql/` to `sys.path` and import `db_config` (minimal bootstrap, shared connection API).
- Authoritative DB path matches `README.md` layout at repository root.

**Validation & Testing**

- `git diff --check`: no conflict-marker / whitespace errors reported on WS-1 diffs.
- Sample diff review (e.g. `bronze_accounts.py`): only connection/bootstrap changed, not SQL.
- Path resolution tested from repo root, `sql/bronze`, and `%TEMP%` — identical resolved DB path.
- Read-only smoke query on authoritative DB: successful.
- Authoritative `product_analytics_light.db`: size **27,537,408** bytes; **not modified** by WS-1 (LastWriteTime unchanged at validation).

**Data Impact**

- No schema, table, or metric changes.
- No ETL execution against authoritative DB required for WS-1.

**Outstanding Issues**

- `data/Test_gold__fact_advanced_activation.py` still uses a manual DB path and legacy `gold__*` table names (not updated in WS-1).
- `sql/__pycache__/` may appear locally after imports; not part of the deliverable.

---

### WS-2: Raw Data Snapshot & Reproducibility

**Status:** Completed

**Objective**  
Make PulseIQ reproducible from version-controlled raw snapshots without depending on an unpublished load process or a local-only DuckDB blob.

**Changes Implemented**

- Exported four `raw__*` tables from the reference DuckDB to Parquet under `data/source_snapshot/`.
- Created `MANIFEST.json` with row counts, column schemas, null counts, file sizes, and SHA-256 checksums.
- Implemented read-only export tool, idempotent loader with staging + transaction, and snapshot validator.
- Documented provenance, load steps, geography gap, and known raw data-quality issues.
- Added minimal `requirements.txt` (`duckdb>=1.0.0`) and pytest-based snapshot tests.
- Updated `README.md` repository tree to reference snapshot layout and new SQL entrypoints.

**Files Created**

- `data/source_snapshot/raw__accounts.parquet`
- `data/source_snapshot/raw__users.parquet`
- `data/source_snapshot/raw__deals.parquet`
- `data/source_snapshot/raw__product_events.parquet`
- `data/source_snapshot/MANIFEST.json`
- `sql/export_raw_snapshot.py`
- `sql/load_raw.py`
- `sql/validate_raw_snapshot.py`
- `docs/data_provenance.md`
- `requirements.txt`
- `tests/test_raw_snapshot.py`

**Files Modified**

- `README.md` — documents `source_snapshot`, `db_config`, load/export/validate scripts.

**Technical Decisions**

- Parquet chosen for efficient, typed columnar storage; export uses DuckDB `COPY ... FORMAT PARQUET` from reference `raw__*` tables.
- Loader validates checksums and null counts against manifest **by column name** (manifest JSON may sort type keys differently from column order).
- Idempotency: `CREATE OR REPLACE` raw tables from staging after validation inside `BEGIN` / `COMMIT` with `ROLLBACK` on failure.
- Geography **not** included in raw snapshot (`raw__geography` does not exist in reference DB; Excel source missing from repo).

**Validation & Testing**

- Raw row counts (reference DB and manifest): `raw__accounts` **120**, `raw__users` **400**, `raw__deals` **6,443**, `raw__product_events` **61,747**.
- `python sql/validate_raw_snapshot.py`: **passed** (files vs manifest).
- Temporary DB: `load_raw.py --db-path` run **twice** — same counts; `validate_raw_snapshot.py --db-path`: **passed**.
- `python -m pytest tests/test_raw_snapshot.py -q`: **2 passed**.
- Authoritative `product_analytics_light.db`: **not modified** (export used read-only connection; loader tests used temp DB only).

**Snapshot sizes (bytes, on disk)**

| File | Size |
|------|-----:|
| `raw__accounts.parquet` | 6,982 |
| `raw__users.parquet` | 18,492 |
| `raw__deals.parquet` | 203,774 |
| `raw__product_events.parquet` | 3,416,046 |
| `MANIFEST.json` | 8,062 |

**Data Impact**

- Raw Parquet files and manifest are **new artifacts**; existing SQL transformations unchanged.
- Documented raw DQ preserved in snapshots: **625** null `event_id`, **653** null `account_id`, **35** duplicate `deal_id` rows.

**Outstanding Issues**

- Full medallion rebuild from Git clone still requires a **geography source** (`sql/data/raw_geography.xlsx` missing; bronze had **8** rows / silver **7** / gold **7** in reference DB at export time).
- Reference `product_analytics_light.db` may remain gitignored on some machines; clones should use `load_raw.py`.
- Re-export updates `snapshot_generated_at_utc` in manifest; checksums stable if source unchanged.

---

### WS-3: Event Identity & Deterministic Surrogate Keys

**Status:** Completed

**Objective**  
Provide a non-null, unique internal event key (`event_sk`) while preserving source `event_id` (including NULL) and without losing or altering raw records.

**Changes Implemented**

- Added deterministic `event_sk` generation in Silver `silver_product_events` pipeline.
- **`SOURCE` rows:** `event_sk = 'SRC-' || event_id` when `event_id` IS NOT NULL.
- **`SURROGATE` rows:** `event_sk = 'SYN-' || sha256(canonical_payload)` with optional `-D{n}` for duplicate payloads (deterministic `ROW_NUMBER` tie-break).
- Added `event_sk_type` (`SOURCE` | `SURROGATE`) on Silver.
- Propagated `EventSk` to `gold_fact_product_events`; retained `EventId` and existing business columns.
- Centralized hash/canonical field SQL in `sql/event_sk_sql.py`.
- Documented methodology in `docs/event_identity.md`.

**Files Created**

- `sql/event_sk_sql.py`
- `docs/event_identity.md`
- `tests/test_event_identity.py`

**Files Modified**

- `sql/silver/silver_product_events.py` — `event_sk` / `event_sk_type`; event category, test filter, and deal-context logic **unchanged**.
- `sql/gold/gold_fact_product_events.py` — added `EventSk`; order by `EventSk`.
- `docs/data_provenance.md` — link to event identity documentation.

**Technical Decisions**

- Surrogates assigned at **Silver** (Bronze/raw remain pass-through; Parquet snapshots untouched).
- Canonical payload excludes `ingested_at` and derived Silver columns for cross-reload stability.
- Non-null source `event_id` values are unique in current data (0 duplicate non-null groups); `SRC-` prefix is sufficient for those rows.
- No orphan quarantine, event rename, activation, or aggregated-fact changes in WS-3.

**Validation & Testing**

- `python -m pytest tests/test_event_identity.py -q`: **4 passed** (temporary DB via `PULSEIQ_DB_PATH`).
- Row counts unchanged: Silver/Gold **60,552** events; raw/bronze **61,747**; null `event_id` / `EventId` **616** after test filter.
- `event_sk`: **0** nulls; **60,552** distinct values; **0** duplicate `event_sk` groups.
- **616** surrogate keys (`SYN-*`); all non-null `event_id` rows use `SRC-{event_id}`.
- Determinism: two consecutive Silver runs on same temp DB produced **identical** ordered `event_sk` lists.
- Authoritative `product_analytics_light.db`: **not modified** by WS-3 tests (LastWriteTime unchanged at WS-3 validation).

**Data Impact**

- **Schema:** Silver + Gold product-event facts gain `event_sk` / `EventSk` (and Silver gains `event_sk_type`).
- **Breaking / migration:** Existing Gold CSV exports and local authoritative DB **do not** include `EventSk` until ETL is re-run on that database. Downstream tools keyed only on `EventId` still see null keys for 616 rows.
- **Metrics:** Activation / TTV logic unchanged (still uses `HasDealContext` and deal dates, not event keys).

**Outstanding Issues**

- `gold_fact_product_events_aggregated` does not expose row-level `event_sk`.
- Local authoritative DB and `exports/gold_csv/fact_product_events.csv` may be stale relative to WS-3 schema until pipeline re-run.
- **641** null `account_id` Silver rows remain (quarantine deferred to WS-5).

---

### WS-4: Event Name Normalization & Canonical Taxonomy

**Status:** Completed

**Objective**  
Establish a consistent event taxonomy with explicit alias mapping while preserving original source event names and row-level grain for product analytics (funnels, engagement, adoption).

**Changes Implemented**

- Added explicit alias map (`ViewDashboard` → `view_dashboard`, `Login` → `login`, `user_login` → `login`) in `sql/event_name_aliases.py`.
- Silver: new `event_name_normalized`; original `event_name` unchanged; categories derived from **normalized** name using case-insensitive patterns (fixes `Login` misclassified as OTHER).
- Gold detail fact: `EventNameNormalized` alongside `EventName`.
- Gold aggregated fact: groups by `EventNameNormalized` + date/category/account; adds `SourceEventNames` (distinct original names) for traceability.
- Documented inventory, rationale, and analytics usage in `docs/event_taxonomy.md`.
- **WS-3 surrogate payload unchanged** in WS-4 (`event_sk` still hashes original `event_name`) — see WS-3 hardening note below.

**Files Created**

- `sql/event_name_aliases.py`
- `docs/event_taxonomy.md`
- `tests/test_event_normalization.py`

**Files Modified**

- `sql/silver/silver_product_events.py` — normalization layer + category rules on normalized names.
- `sql/gold/gold_fact_product_events.py` — `EventNameNormalized`.
- `sql/gold/gold_fact_product_events_aggregated.py` — canonical grouping + `SourceEventNames`.

**Technical Decisions**

- Only **three** documented aliases; unmapped names pass through unchanged (no broad lowercasing).
- Categories applied to `event_name_normalized`, not raw string — justified correction for `Login` → AUTH only.
- Aggregation grain intentionally coarser than detail; detail row count unchanged.
- `event_sk` determinism preserved by not altering WS-3 hash inputs in this workstream.

**Validation & Testing**

- Read-only audit: **10** distinct raw (non-test) event names; frequencies match prior audit (e.g. `login` 3861, `ViewDashboard` 118, `Login` 83, `user_login` 59).
- `python -m pytest tests/test_event_normalization.py tests/test_event_identity.py -q`: **9 passed**.
- Silver/Gold detail: **60,552** rows before/after normalization; **7** canonical normalized names.
- Aggregated `SUM(EventCount)` = **60,552** = detail row count; aggregated **group** count **30,797** (down from **30,915** in pre–WS-4 CSV export baseline due to alias merge).
- Authoritative `product_analytics_light.db`: **not modified** (tests use temporary DB).

**Data Impact**

- **Schema:** Silver + Gold detail gain normalized name column; aggregated fact replaces `EventName` group key with `EventNameNormalized` + `SourceEventNames`.
- **Breaking / migration:** Existing Gold CSV exports omit `EventNameNormalized` until ETL re-run; aggregated CSV schema changes grouping columns.
- **Metrics:** Activation / TTV unchanged (not keyed on event names).

**Outstanding Issues**

- `view_dashboard` remains category OTHER (no new product-view category introduced).
- Null `account_id` / quarantine deferred to WS-5.
- **WS-3 hardening (planned, not implemented in WS-4):** Canonical payload uses `coalesce(..., '')` which treats NULL and empty string identically in hashes; typed JSON serialization recommended if re-ingestion introduces ambiguous nulls — would change `SYN-*` keys and require manifest restatement.

---

### WS-4.1: Aggregated Gold Schema Compatibility Cleanup

**Status:** Completed

**Objective**  
Align documentation, requirements, CSV export naming, and automated tests with the WS-4 aggregated Gold schema (`EventNameNormalized`, `SourceEventNames`) without changing normalization or activation logic.

**Changes Implemented**

- Documented aggregated and detail Gold column contracts in `sql/gold_table_schemas.py`.
- Updated `export_gold_to_csv.py` to write portfolio CSV filenames (e.g. `fact_product_events_aggregated.csv`); optional `PULSEIQ_EXPORT_DIR` and `PULSEIQ_EXPORT_TABLES`; skips tables missing from the target database.
- Updated `requirements.md` FR9, `README.md`, `docs/event_identity.md`, and `docs/data_provenance.md` to replace outdated `EventName`-only aggregation references.
- Added `tests/test_gold_aggregated_schema.py` for schema validation, EventCount reconciliation, and CSV header verification.

**Files Created**

- `sql/gold_table_schemas.py`
- `tests/test_gold_aggregated_schema.py`

**Files Modified**

- `sql/gold/export_gold_to_csv.py`
- `requirements.md`
- `README.md`
- `docs/event_identity.md`
- `docs/data_provenance.md`
- `CHANGES.md`

**Technical Decisions**

- Aggregated grain remains WS-4 canonical grouping; no SQL transformation changes.
- Export filenames match existing `exports/gold_csv/` convention rather than raw DuckDB table names.

**Validation & Testing**

- `python -m pytest tests/test_gold_aggregated_schema.py -q`: **4 passed** (temporary DB + export to temp directory).
- Aggregated schema columns verified in order: `EventDate`, `EventNameNormalized`, `EventCategory`, `AccountId`, `EventCount`, `UniqueUsers`, `SourceEventNames`.
- `SUM(EventCount)` = **60,552** = detail fact row count.
- Authoritative `product_analytics_light.db`: **not modified**.

**Data Impact**

- Documentation and export behavior only; committed `exports/gold_csv/*.csv` under repo may remain stale until a deliberate ETL + export on dev DB.
- Power BI models expecting aggregated `EventName` must remap to `EventNameNormalized` / `SourceEventNames`.

**Outstanding Issues**

- Local `exports/gold_csv/fact_product_events_aggregated.csv` still reflects pre–WS-4 header until re-exported.
- `gold_fact_product_events.csv` export will gain `EventSk` / `EventNameNormalized` columns after full Gold rebuild.

---

### WS-5: Orphan Event Resolution & Quarantine Audit

**Status:** Audit Completed — Implementation Pending

**Objective**  
Investigate events with missing `account_id` and define quarantine / resolution policy. **No SQL or Python implementation in this workstream.**

**Audit methodology**  
Read-only SQL against authoritative `product_analytics_light.db`. Verified **2026-11-05**.

**Reconciled baseline**

| Layer | Total | NULL account | NULL user | NULL deal | NULL event_id |
|-------|------:|-------------:|----------:|----------:|--------------:|
| Raw (all) | 61,747 | 653 | — | — | 625 |
| Raw (non-test) | 60,552 | 641 | — | — | 616 |
| Bronze | 61,747 | 653 | — | — | 625 |
| Silver | 60,552 | 641 | 1,151 | 24,261 | 616 |
| Gold detail | 60,552 | 641 | 1,151 | 24,261 | 616 |

**653 vs 641:** Silver drops **1,195** test events; **12** null-account rows are test → **653 − 12 = 641**.

**NULL account ∩ NULL event_id (non-test / Silver):** **7** / **634** / **609** (both null / account null only / event null only).

**Invalid account reference** (non-null account not in `gold_dim_accounts`): **0**.

**User resolution (orphans n=641):** **622** mappable to valid user→account; **9** user dim null account; **10** null `user_id`.

**Deal resolution:** **416** with `deal_id`; **325** distinct deal keys; all map to one account in `raw__deals`. **35** duplicate `deal_id` rows in deals (**0** multi-account groups). Avoid naive join to `gold_fact_deals` (fan-out **641→645**).

**Cross-validation (deduped deal account):** CONSISTENT **0**, USER_ONLY **216**, DEAL_ONLY **10**, CONFLICTING **406**, UNRESOLVED **9**.

**Recommended policy (pending implementation)**  
Quarantine **406** conflicts; optional enrich **216** user-only / **10** deal-only with governance; exclude unresolved orphans from account-level metrics; preserve source `account_id`.

**Changes Implemented**  
*(Audit documentation only — see final report and future WS-5 implementation.)*

**Files Created / Modified (code)**  
*(None.)*

**Validation & Testing**  
Ad-hoc read-only SQL reconciliation only.

**Outstanding Issues**  
Implementation of `account_id_resolved`, quarantine table, and Gold filters not started. Authoritative Silver may lack WS-3 `event_sk` until ETL re-run.

---

### WS-5.1: Orphan Classification Reconciliation Audit

**Status:** Audit Completed — Implementation Pending

**Objective**  
Verify WS-5 orphan buckets are **mutually exclusive**, **exhaustive**, and reconcile sub-cohorts (null `user_id`, user-dim null account, enrichable **226**).

**Method**  
Read-only SQL on authoritative `product_analytics_light.db` (classification keyed at event-record grain). **`641` is the count of orphan event records** (Silver rows with NULL source `account_id`), not “641 distinct non-null source EventIds”; internal identifier is **`event_sk`**. `EventSk` lists verified on a **temporary** DuckDB built from Parquet snapshots + current Silver script (not written to authoritative DB).

**Mutually exclusive primary classification (n=641)**

| resolution_status | Count | Null UserId rows | Null DealId rows | User-dim null account rows |
|-------------------|------:|-----------------:|-----------------:|---------------------------:|
| USER_ONLY | **216** | 0 | **216** | 0 |
| DEAL_ONLY | **10** | **2** | 0 | **8** |
| CONFLICTING | **406** | 0 | 0 | 0 |
| UNRESOLVED | **9** | **8** | **9** | **1** |
| CONSISTENT | **0** | 0 | 0 | 0 |
| **Total** | **641** | **10** | **225** | **9** |

**Partition check:** **216 + 10 + 406 + 9 + 0 = 641**; each orphan assigned exactly one status (**641** orphan records at Silver grain; **641** distinct `event_sk` on snapshot-backed temp DB).

**Sub-cohort intersections (verified)**  
- **10** null `user_id` = **2** DEAL_ONLY + **8** UNRESOLVED (disjoint).  
- **9** user-dim null `AccountId` = **8** DEAL_ONLY (has `user_id`) + **1** UNRESOLVED (disjoint with CONFLICTING).  
- **622** valid user→account = **216** USER_ONLY + **406** CONFLICTING.

**Policy-safe enrichable (unambiguous single source)**  
- **216** USER_ONLY: valid user account; **no** `deal_id` on event.  
- **10** DEAL_ONLY: unambiguous deal→account; **no** valid user account.  
- **226 = 216 + 10** excludes **406** CONFLICTING and **9** UNRESOLVED.

**EventSk note**  
Authoritative Silver lacks `event_sk` until ETL re-run; sample `EventSk` per bucket confirmed via temp pipeline (e.g. USER_ONLY `SRC-01f022a6-…`, CONFLICTING `SRC-004b4eee-…`).

**Changes Implemented**  
Documentation only (`CHANGES.md`).

---

### WS-5.2: Account Attribution & Event Quarantine

**Status:** Completed

**Objective**  
Implement orphan account resolution and quarantine on Silver product events; expose resolved attribution in Gold detail; preserve all **60,552** events and source `account_id`.

**Pre-implementation validation**  
WS-5.1 buckets re-verified on temporary DuckDB from Parquet snapshots (**60,552** Silver rows; **59,911** SOURCE_VERIFIED path; orphan buckets **216 / 10 / 406 / 9**). Geography: `sql/data/raw_geography.xlsx` absent — tests stub `bronze_geography` / `silver_geography` from account country codes (documented in `docs/orphan_events.md`).

**Changes Implemented**

- **`sql/account_resolution_sql.py`** — CTEs and CASE logic for attribution (deduped deal→account map; user dim map).
- **`sql/silver/silver_product_events.py`** — columns `account_id_resolved`, `account_resolution_status`, `account_resolution_method`, `account_resolution_reason`; view **`silver_product_events_quarantine`**.
- **`sql/gold/gold_fact_product_events.py`** — `AccountIdResolved`, `AccountResolutionStatus`, `AccountResolutionMethod`, `AccountResolutionReason` (source `AccountId` unchanged).
- **`sql/gold_table_schemas.py`** — detail schema includes resolution columns.
- **`docs/orphan_events.md`** — problem, rules, analytics guidance, validation.
- **`tests/pipeline_helpers.py`**, **`tests/test_orphan_quarantine.py`** — full attribution test suite; existing event tests use minimal pipeline (bronze accounts/users + silver users before product events).

**Verified counts (temp DB, post-implementation)**

| account_resolution_status | Count |
|---------------------------|------:|
| SOURCE_VERIFIED | 59,911 |
| ENRICHED | 226 |
| QUARANTINED | 415 |
| **Total** | **60,552** |

Quarantine view: **415**. Enrichment reasons: **216** `USER_ACCOUNT_ONLY`, **10** `DEAL_ACCOUNT_ONLY`. Quarantine reasons: **406** `CONFLICTING_USER_DEAL_ACCOUNTS`, **9** `NO_VALID_ACCOUNT_REFERENCE`. Invalid source quarantine: **0**.

**Files Modified**  
`sql/silver/silver_product_events.py`, `sql/gold/gold_fact_product_events.py`, `sql/gold_table_schemas.py`, `tests/test_event_identity.py`, `tests/test_event_normalization.py`, `tests/test_gold_aggregated_schema.py`, `CHANGES.md`.

**Files Created**  
`sql/account_resolution_sql.py`, `docs/orphan_events.md`, `tests/pipeline_helpers.py`, `tests/test_orphan_quarantine.py`.

**Validation & Testing**  
`python -m pytest tests/ -q` — **25 passed** (includes 10 WS-5.2 quarantine tests). Authoritative `product_analytics_light.db` not modified by tests.

**Data Impact**  
Re-run Silver/Gold on a target DuckDB to materialize new columns; aggregated Gold and activation unchanged in this workstream.

**Outstanding Issues**  
Full end-to-end pipeline still requires geography source or stub for `silver_accounts`; authoritative dev DB may lack new columns until ETL re-run. WS-5 umbrella “quarantine table” policy is implemented as Silver columns + quarantine **view** (not a separate physical table).

---

### WS-6: Feature Property Preservation & Product Instrumentation

**Status:** Completed

**Objective**  
Preserve original `event_properties` JSON and expose typed product fields in Gold for feature adoption and behavioural analytics.

**Pre-implementation audit (snapshot temp DB, n=60,552 Silver events)**  
All rows have non-null JSON; **0** invalid parses in source data. Keys: `feature_name`, `source`, `pipeline_id`, `stage_id`. **4** distinct `feature_name` values (dashboard, pipeline, automation, deal); **3** JSON `source` values (ui, api, automation). **24,156** rows with pipeline/stage IDs.

**Changes Implemented**

- **`sql/event_properties_sql.py`** — shared parse status + JSON extract expressions.
- **`sql/silver/silver_product_events.py`** — `with_parsed_properties` CTE; columns `event_properties_parse_status`, `feature_name`, `event_source`, `pipeline_id`, `stage_id`; original `event_properties` unchanged.
- **`sql/gold/gold_fact_product_events.py`** — `EventProperties`, `EventPropertiesParseStatus`, `FeatureName`, `EventSource`, `PipelineId`, `StageId`.
- **`sql/gold/gold_fact_product_events_aggregated.py`** — grain adds **`FeatureName`**; source **`AccountId`** semantics unchanged.
- **`sql/gold_table_schemas.py`** — updated detail/aggregated column contracts.
- **`docs/feature_adoption.md`** — inventory, adoption definitions, example SQL.
- **`tests/test_feature_properties.py`**, **`tests/pipeline_helpers.run_ws6_gold_pipeline`**.

**Aggregated row counts**

| | Groups | SUM(EventCount) |
|--|-------:|----------------:|
| Pre-WS-6 | 30,797 | 60,552 |
| WS-6 | **49,300** | **60,552** |

**Invalid JSON handling**  
`event_properties_parse_status` = `INVALID_JSON` when payload is non-null but `TRY_CAST` fails; extracted columns NULL; raw JSON retained.

**Validation & Testing**  
`python -m pytest tests/ -q` — includes WS-6 feature property tests; authoritative DB not modified.

**Data Impact**  
Re-run Silver/Gold on target DuckDB for new columns; activation/TTV/account-resolution logic unchanged.

**Future (not in WS-6)**  
Funnel metrics, pipeline dimension joins, aggregated global distinct-user rollups — see `docs/feature_adoption.md`.

---

### WS-7: Date & Tenure Consistency

**Status:** Completed

**Objective**  
Central **`as_of_date`** for reproducible age, tenure, and recency; separate user vs account tenure; open-only `deal_age_days`; recency fix for future `last_seen_at`; DAX calendar aligned to **`2026-07-11`**.

**Configuration**

- `db_config.get_as_of_date()` — default **`2026-07-11`**, override **`PULSEIQ_AS_OF_DATE`** (ISO only).
- `sql/as_of_date_sql.py` — DuckDB `DATE` literal from validated Python date.

**Silver / Gold changes**

- **`silver_accounts`**: `is_future_created`; future accounts → **NULL** `account_age_days` (was `0`).
- **`silver_users`**: `account_tenure_days`, `is_future_created`; recency **`future_last_seen`**; no negative active buckets.
- **`silver_deals`**: `is_future_created`; **`deal_age_days` NULL when closed** (breaking vs pre–WS-7 closed-deal age).
- **Gold**: `AccountTenureDays`, `IsFutureCreated` on dims/deals fact.

**Backward compatibility**

| Field | Change |
|-------|--------|
| Future account/user age | `0` → **NULL** |
| Closed deal `deal_age_days` | numeric → **NULL** (use `DealCycleDays`) |
| Recency | future last seen → **`future_last_seen`**, not `<7 days` |

**Activation regression (temp DB, both as_of values)**  
**21 / 120** activated; mean TTV **~9.904762** — unchanged.

**Documentation**  
`docs/date_and_tenure.md`; `requirements.md` FR2/FR3/FR4; `data/dim_date.txt` (`ReportAsOfDate` constant).

**Tests**  
`tests/test_as_of_date.py`; `tests/pipeline_helpers.run_lifecycle_pipeline`.

**Files Created**  
`sql/as_of_date_sql.py`, `docs/date_and_tenure.md`, `tests/test_as_of_date.py`.

**Files Modified**  
`sql/db_config.py`, `sql/silver/silver_accounts.py`, `sql/silver/silver_users.py`, `sql/silver/silver_deals.py`, `sql/gold/gold_dim_accounts.py`, `sql/gold/gold_dim_users.py`, `sql/gold/gold_fact_deals.py`, `data/dim_date.txt`, `tests/pipeline_helpers.py`, `requirements.md`, `CHANGES.md`.

**Validation**  
`python -m pytest tests/ -q` — all tests including WS-7; authoritative DB not modified by tests.

---

### WS-8: Activation & TTV Analytics Audit

**Status:** Audit Completed — Implementation Pending

**Objective**  
Audit account-level advanced activation and Time-to-Value before expanding the analytics model. Read-only; baseline re-verified on temp DuckDB (snapshots + lifecycle pipeline).

**Verified full-dataset baseline**

| Metric | Value |
|--------|------:|
| Accounts | 120 |
| Activated | 21 |
| Rate | 17.5% |
| Mean TTV (activated) | ~9.904762 days |

**Cohort maturity (`as_of_date = 2026-07-11`)**  
16 accounts existed on as-of; 15 had complete 14-day windows; **0** activated among window-complete accounts; all **21** activated accounts have `CreatedDate` **after** 2026-07-11.

**Deal duplicates**  
35 duplicate `deal_id` groups do not change `FirstDealDate` or activation/TTV; `DealsInFirst14Days` counts can exceed distinct deals.

**Attribution**  
Activation uses source **`AccountId`** only; enriched-account counterfactual still **21** activated.

**Changes Implemented**  
Documentation only (`CHANGES.md` + audit report).

**Outstanding (post–WS-8 audit)**  
Addressed in WS-8.1 (as-of fact + `docs/metrics.md` + tests). User-level activation still pending.

---

### WS-8.1: Activation Metrics & Cohort Maturity

**Status:** Completed

**Objective**  
Supplementary **`gold_fact_activation_as_of`** distinguishing full-dataset activation (metric A) from as-of eligible 14-day activation (metric B) without changing `gold_fact_advanced_activation`.

**Implementation**

- **`sql/gold/gold_fact_activation_as_of.py`** — one row per account; `ReportAsOfDate` from `get_as_of_date()`; maturity flags; `IsActivatedFullDataset` / `IsActivatedAsOf`; TTV pass-through from advanced activation.
- **`docs/metrics.md`** — definitions, denominators, cohort maturity, limitation that **17.5% is not July 2026 as-of rate**.
- **`tests/test_activation_as_of.py`** — baseline, cohort **0/15**, schema, segments, determinism, advanced activation unchanged on re-run.
- **`sql/gold_table_schemas.py`**, **`export_gold_to_csv.py`** — schema contract + `fact_activation_as_of.csv`.

**Verified (temp DB, `PULSEIQ_AS_OF_DATE=2026-07-11`)**

| Metric | Value |
|--------|------:|
| Full-dataset activated | **21 / 120** (17.5%) |
| Mean / median TTV (activated) | **~9.904762** / **10** days |
| Eligible as-of | **15** |
| As-of activated | **0** (0%) |
| Created by as-of / after as-of | **16** / **104** |
| Incomplete window | **1** |

**Validation**  
`python -m pytest tests/test_activation_as_of.py -q` (and full suite). Authoritative DB not modified by tests.

---

### WS-8.2: Activation As-Of TTV Semantics

**Status:** Completed

**Objective**  
Clarify TTV columns on `gold_fact_activation_as_of` without changing advanced activation or activation flags.

**Changes**

- Renamed pass-through **`TimeToValueDays`** → **`TimeToValueDaysFullDataset`** (same values as `gold_fact_advanced_activation.TimeToValueDays`).
- Added **`TimeToValueDaysAsOf`**: populated only when `IsEligibleAsOf` AND `IsActivatedAsOf`; otherwise NULL.
- Updated **`sql/gold_table_schemas.py`**, **`docs/metrics.md`**, **`tests/test_activation_as_of.py`**.

**Verified**  
21/120 and 0/15 unchanged; full-dataset mean TTV ~9.904762; all **`TimeToValueDaysAsOf`** NULL on reference snapshot (0 eligible activated).

**Files modified**  
`sql/gold/gold_fact_activation_as_of.py`, `sql/gold_table_schemas.py`, `docs/metrics.md`, `tests/test_activation_as_of.py`, `CHANGES.md`.

---

### WS-9: Automated Data Quality & Metric Contracts

**Status:** Completed

**Objective**  
Consolidate warehouse-wide data-quality checks and document implemented metric contracts without changing business definitions.

**Pre-audit**  
~59 tests across WS-2–WS-8.2; retained all existing modules; added cross-layer contracts and export validation.

**Created**

- `tests/test_data_quality_contracts.py` — raw→bronze→silver→gold reconciliation, manifest known DQ, deal duplicates, activation/as-of contracts.
- `tests/test_export_contracts.py` — full/partial CSV export, headers vs DuckDB, TTV columns, agg `EventCount` reconcile.
- `docs/metric_contracts.md` — IMPLEMENTED / PARTIAL / PROPOSED index (canonical activation narrative remains `docs/metrics.md`).

**Modified**

- `tests/pipeline_helpers.py` — `run_full_dq_pipeline()`.
- `CHANGES.md`.

**Contracts verified (temp DB, default as-of 2026-07-11)**

| Check | Expected |
|-------|----------|
| Raw / bronze events | 61,747 |
| Silver events | 60,552 |
| Attribution | 59,911 + 226 + 415 |
| Gold detail / SUM(agg) | 60,552 |
| Activation A | 21/120, mean TTV ~9.904762, median 10 |
| Activation B | 0/15; `TimeToValueDaysAsOf` all NULL |
| Duplicate deal_id groups | 35 (single account each) |

**Known exceptions (documented, not failures)**  
Manifest: 625 null `event_id`, 653 null `account_id`, 35 duplicate deal rows; geography test stub when Excel absent.

**Validation**  
`python -m pytest tests/ -q` — full suite passes on temp DuckDB only; authoritative DB untouched.

**Outstanding (WS-10+)**  
Single `run_pipeline.py`, global DAU as curated metric, user-level activation.

---

### WS-10: Pipeline Orchestration & End-to-End Reproducibility

**Status:** Completed

**Objective**  
Single entry point for raw validation through Gold export with DB safety, geography modes, DQ gates, and JSON run reports.

**Created**

- `run_pipeline.py` — CLI orchestrator (`--db-path`, `--as-of-date`, `--geography-mode`, `--export-dir`, `--dry-run`).
- `sql/pipeline/` — `runner.py`, `stages.py`, `safety.py`, `geography.py`, `dq_validation.py`, `export_validation.py`.
- `docs/RUNBOOK.md`, `docs/pipeline_architecture.md`.
- `tests/test_pipeline_orchestration.py`.

**Modified**

- `tests/pipeline_helpers.py` — shared `apply_derived_geography_fixture`.
- `README.md` — getting started.

**Dependency order (verified)**  
`validate_raw_snapshot` → `load_raw` → bronze (accounts, users, deals, product_events) → geography (mode) → silver (geography if source, accounts, users, deals, product_events) → gold (dims, deals, events, agg, activation, activation_as_of, dim_geography) → `export_gold_to_csv` → pipeline DQ → export validation.

**Safety**

- Explicit `--db-path` or `PULSEIQ_DB_PATH` required for real runs.
- Refuses `product_analytics_light.db` unless `--allow-authoritative-db` or `PULSEIQ_ALLOW_AUTHORITATIVE_DB=1`.
- Default CSV output: `artifacts/gold_csv` (not committed `exports/gold_csv`).

**Geography**

- `derived-fixture` (default): account-country stub (documented limitation).
- `source`: requires `sql/data/raw_geography.xlsx` or fails fast.

**Validation**

- `python -m pytest tests/ -q` → **85 passed**.
- `python run_pipeline.py --db-path artifacts/ws10_pulseiq.duckdb ...` → success; report under `artifacts/pipeline_runs/`.
- Baseline counts unchanged (60,552 events, 21/120 activation, 0/15 as-of).

**Idempotency**  
Stages use `CREATE OR REPLACE`; safe to rerun on same disposable DB. Failed runs halt before success reporting; partial exports fail export validation.

**Outstanding (Phase 1+)**  
Orchestrated scheduling/CI, geography Excel in repo, optional skip flags per stage.

---

### WS-11: Product Analytics Coverage Audit & Metric Specification

**Status:** Completed

**Scope**  
Read-only Phase 1 audit: data foundation, metric feasibility, product questions, and implementation roadmap. **No** SQL/transform/test/pipeline/snapshot/authoritative-DB changes.

**Created**

- `docs/analytics_coverage_audit.md` — executive summary, identity/taxonomy/time assessment, feasibility matrix, product Q&A, limitations.
- `docs/product_analytics_metric_specification.md` — per-metric definitions, grains, attribution, status (IMPLEMENTED through NOT_FEASIBLE), P0/P1/P2 roadmap.

**Data inspected**

- Disposable DB `artifacts/ws10_pulseiq.duckdb` (read-only queries).
- Pipeline report `artifacts/pipeline_runs/d0d0ace84e32.json`.
- Manifest, Gold schemas, existing docs and tests (reference).

**Key findings (verified)**

- Attribution: 59,911 / 226 / 415 = 60,552.
- Activation unchanged: 21/120 (17.5%), as-of 0/15; mean TTV ~9.904762.
- 1,151 events null `UserId` (1,141 SOURCE_VERIFIED) — user metrics need explicit filter.
- Event dates 2026–2029; 104/120 accounts future at default as-of — full-dataset ≠ as-of narratives.
- Seven canonical events + four feature areas; first account event rarely `login`.
- Global DAU/retention/funnel summaries **not** in Gold; **implementable** from detail fact with caveats.

**Limitations**  
Synthetic data, derived geography fixture, no causal/experiment metrics, aggregated `UniqueUsers` not global DAU.

**Next**  
WS-12: implement P0 engagement + feature adoption metrics per specification (not started in WS-11).

---

### WS-12: Core Product Engagement & Feature Analytics

**Status:** Completed

**Scope**  
Phase 1 Gold models for engagement (DAU/WAU/MAU), feature adoption, breadth, and product activity recency. **No** changes to activation logic, Silver attribution, or raw snapshots.

**Created (Gold)**

- `gold_fact_engagement_periodic` — DAY / calendar WEEK / calendar MONTH; USER and ACCOUNT; OFFICIAL + SENSITIVITY; FULL_DATASET + AS_OF.
- `gold_fact_feature_adoption_account` / `gold_fact_feature_adoption_user`.
- `gold_fact_feature_adoption_by_period` — monthly distinct adoption (not sum of daily).
- `gold_fact_feature_breadth_account` / `gold_fact_feature_breadth_user`.
- `gold_fact_product_activity_recency_account` / `gold_fact_product_activity_recency_user`.
- `sql/product_analytics_sql.py` — shared attribution predicates.

**Modified**

- `sql/pipeline/stages.py`, `sql/gold/export_gold_to_csv.py`, `sql/gold_table_schemas.py`, `tests/pipeline_helpers.py`.
- Docs: `product_analytics_metric_specification.md`, `metric_contracts.md`, `feature_adoption.md`, `README.md`.

**Tests**  
`tests/test_ws12_product_analytics.py` (10). Full suite: **95 passed**.

**Implementation decisions**

- Qualified engagement: all product event types (including `login`).
- WAU/MONTH: **calendar ISO week** (Mon start) and **calendar month** (WS-11 allowed rolling; calendar chosen and documented).
- User OFFICIAL: SOURCE_VERIFIED + non-null `UserId`; user SENSITIVITY adds ENRICHED; QUARANTINED excluded.
- Account OFFICIAL: SOURCE_VERIFIED + `AccountId`; sensitivity uses `AccountIdResolved` for ENRICHED.

**Reconciliation**

- Attribution: 59,911 / 226 / 415 unchanged.
- Activation: 21/120, as-of 0/15, mean TTV ~9.904762 unchanged.
- Pipeline idempotence verified on `artifacts/ws12_test.duckdb` (two runs).

---

### WS-13: Retention, Funnel & Segment Analytics

**Status:** Completed

**Chronology gate (required)**  
Documented in `docs/chronology_integrity_audit.md`: **31,161** PRE_CREATION account events; **104** future accounts with pre-as-of events. WS-12 AS_OF adoption incorrectly showed **120** accounts — **corrected to 15** distinct adopters (16 eligible by create date).

**Created**

- `gold_fact_qualified_product_events` — chronology flags + qualified booleans.
- `gold_fact_retention_cohort` — account/user D7/D14 exact-day retention.
- `gold_fact_account_workflow_funnel` — descriptive non-causal funnel.
- `gold_fact_segment_product_metrics` — SMB / MID-MARKET comparisons.
- `docs/chronology_integrity_audit.md`, `docs/retention_and_cohort_analysis.md`, `docs/product_funnel_analysis.md`.

**Modified (WS-12 chronology fix)**

- All WS-12 product analytics Gold scripts; `sql/product_analytics_sql.py`; pipeline stage order; exports/schemas; tests.

**Validation**  
`python -m pytest tests/ -q` → **102 passed**; pipeline success on disposable DB; activation unchanged.

**Segment AS_OF**  
Eligible accounts **16** (SMB + MID-MARKET reconcile to 16); active accounts ≤ eligible.

---

### WS-14: Product Insights & Decision Intelligence

**Status:** Completed

**Scope**  
Read-only interpretation of Gold analytics; product opportunities, prioritisation, two PRD sketches, roadmap. **No** SQL, snapshots, authoritative DB, or export changes.

**Evidence reviewed**  
Qualified engagement/adoption, retention D7/D14, descriptive funnel, segment metrics, FR10 activation — disposable DB; contexts **FULL_DATASET** vs **AS_OF 2026-07-11** kept separate.

**Major findings**  
- AS_OF: **15/16** mature accounts with feature adoption; **0/15** FR10 eligible activation.  
- Account exact-day D7/D14 retention **0%** on mature cohort; user D7 **~3.6%**.  
- Funnel stage **reach** high on deal actions; not ordered conversion.  
- Full-dataset activation **21/120 (17.5%)** ≠ as-of story.

**Created**  
`docs/product_insights_and_recommendations.md`, `docs/product_opportunity_backlog.md`, `docs/product_requirements_proposals.md`, `docs/product_roadmap.md`.

**Modified**  
`README.md`, `CHANGES.md`.

**Prioritisation**  
P0: activation milestone guide (OPP-01); P1: rolling retention measurement + dashboard depth; P2: segment onboarding.

**Limitations**  
Synthetic data; as-of **n=16** accounts; no causal/experiment results.

---

### WS-15: Final Dashboard & Portfolio Packaging

**Status:** Completed (**final workstream**)

**Scope**  
Portfolio packaging only: Power BI CSV handoff, semantic/measure documentation, case study, README rewrite, demo script, export manifest generator. **No** Bronze/Silver/Gold SQL changes; **no** authoritative DB or committed `exports/gold_csv` overwrite.

**Environment**  
Power BI Desktop **not** detected on build machine — **no** validated `.pbix` / `.pbip` committed.

**Pipeline validation**  
- Disposable DB: `artifacts/ws15_final.duckdb`  
- Exports: `artifacts/ws15_powerbi_exports/`  
- Args: `--as-of-date 2026-07-11`, `--geography-mode derived-fixture`  
- Manifest: `POWERBI_EXPORT_MANIFEST.json` (schema + row counts vs DuckDB)

**Created**  
`scripts/generate_powerbi_export_manifest.py`; `powerbi/`; `docs/pulseiq_case_study.md`, `docs/demo_walkthrough.md`, `docs/powerbi_setup.md`, `docs/powerbi_measure_catalog.md`, `docs/powerbi_data_dictionary.md`, `docs/diagrams/pulseiq_architecture.mmd`.

**Modified**  
`README.md`, `CHANGES.md` (this entry).

**Dashboard handoff**  
Six-page report spec in `docs/powerbi_setup.md`; DAX in `docs/powerbi_measure_catalog.md`. Build report in Power BI Desktop locally.

**Preserved evidence rules**  
Synthetic disclosure; chronology-qualified official metrics; FULL_DATASET vs AS_OF; FR10 **21/120 (17.5%)** vs as-of **0/15**; exact-day retention; descriptive funnel; as-of **n=16** sample visible.

**Tests**  
`python -m pytest tests/ -q` → **102 passed** (~12 min; WS-15 code: manifest script only).

**Limitations**  
No shipped PBIX; screenshots manual post-build; large artifacts under `artifacts/` remain local.

---

## Future phases

None planned — **PulseIQ complete after WS-15**.

---

*Last updated: WS-15 final dashboard and portfolio packaging.*
