# PulseIQ — Data Provenance & Raw Snapshot Reproducibility

## Dataset origin

PulseIQ uses a **synthetic B2B SaaS CRM** dataset created for portfolio and case-study work. It simulates accounts, users, deals, and product events for a European-centric CRM product (see `README.md`). The data are **not** sourced from a live production system.

The authoritative reference database during snapshot creation was:

- `product_analytics_light.db` (repository root)

Raw operational tables inside that database: `raw__accounts`, `raw__users`, `raw__deals`, `raw__product_events`.

## Versioned raw snapshots

Canonical raw extracts live under:

```text
data/source_snapshot/
  raw__accounts.parquet
  raw__users.parquet
  raw__deals.parquet
  raw__product_events.parquet
  MANIFEST.json
```

Each Parquet file is a **byte-preserving logical export** of the corresponding `raw__*` table: same columns, types, nulls, and row counts as documented in `MANIFEST.json`. No deduplication, filtering, or business rules are applied at export time.

### Snapshot generation procedure

From the repository root, with the reference DuckDB available:

```bash
python sql/export_raw_snapshot.py
```

This opens the source database **read-only**, writes Parquet files, and regenerates `MANIFEST.json` (checksums, schema, null counts, row counts).

**Do not** run export against a database you intend to treat as read-only production unless you accept rewritten manifest timestamps.

## Loading raw tables

To build a **new** DuckDB file from snapshots (recommended for clean clones):

```bash
python sql/load_raw.py --db-path path/to/new_pulseiq.duckdb
```

Or set `PULSEIQ_DB_PATH` and run:

```bash
python sql/load_raw.py
```

The loader:

1. Validates file presence and SHA-256 checksums against `MANIFEST.json`
2. Validates schema, row counts, and null counts
3. Loads via staging tables inside a transaction (failed loads roll back)
4. Replaces `raw__*` tables idempotently (safe to run twice on the same target DB)

Validate snapshots (and optionally a loaded DB):

```bash
python sql/validate_raw_snapshot.py
python sql/validate_raw_snapshot.py --db-path path/to/new_pulseiq.duckdb
```

## Table inventory (raw snapshot baseline)

| Table | Rows | Primary identifier | Notes |
|-------|-----:|--------------------|-------|
| `raw__accounts` | 120 | `account_id` | Unique IDs |
| `raw__users` | 400 | `user_id` | Unique IDs; 3 null `account_id` |
| `raw__deals` | 6,443 | `deal_id` | 35 duplicate `deal_id` values (see DQ) |
| `raw__product_events` | 61,747 | `event_id` | 625 null `event_id`; 653 null `account_id` |

Full column lists, types, and null counts are in `MANIFEST.json`.

## Geography limitation

- **`raw__geography` does not exist** in the reference database.
- Bronze geography is loaded from **`sql/data/raw_geography.xlsx`**, which is **not** in the repository.
- In the reference database at snapshot time: `bronze_geography` = **8** rows, `silver_geography` = **7** rows, `gold_dim_geography` = **7** rows.

**Geography is not part of the raw Parquet snapshot.** Rebuilding the full medallion pipeline from snapshots alone requires a separate geography source (restore Excel, or a future documented reference export from `bronze_geography`). **Do not** treat Gold dimension rows as original raw input.

## Event identity (WS-3)

Silver and Gold product-event tables expose an internal **`event_sk`** / **`EventSk`** while preserving source **`event_id`** / **`EventId`** (including NULLs). See [event_identity.md](event_identity.md). Normalized event names: [event_taxonomy.md](event_taxonomy.md).

## Known data-quality issues (preserved in raw snapshots)

These are intentional inputs for later workstreams (WS-3+); WS-2 does not fix them:

| Issue | Table | Count |
|-------|-------|------:|
| Null `event_id` | `raw__product_events` | 625 |
| Null `account_id` | `raw__product_events` | 653 |
| Duplicate `deal_id` values | `raw__deals` | 35 extra rows vs distinct IDs |

## Reproducibility from a clean Git clone

1. Clone the repository (includes `data/source_snapshot/` and `MANIFEST.json`).
2. Install Python dependencies (`duckdb` minimum; see `requirements.txt` when present).
3. Create a new database: `python sql/load_raw.py --db-path ./product_analytics_light.db` **only on a new file** if you wish to avoid overwriting an existing local reference DB.
4. Run `python sql/validate_raw_snapshot.py --db-path ./product_analytics_light.db`.
5. Run Bronze → Silver → Gold scripts separately (not part of WS-2).
6. Export Gold CSVs: `python sql/gold/export_gold_to_csv.py` (writes to `exports/gold_csv/` using filenames in `sql/gold_table_schemas.py`). Optional env: `PULSEIQ_EXPORT_DIR`, `PULSEIQ_EXPORT_TABLES` (comma-separated).

Aggregated export columns: `EventDate`, `EventNameNormalized`, `EventCategory`, `AccountId`, `EventCount`, `UniqueUsers`, `SourceEventNames`.

The bundled reference `product_analytics_light.db` may still exist locally for development but is **not required** if snapshots are present.

## Sensitive fields

Raw snapshots may contain synthetic person fields (e.g. user names, email domains). Treat snapshots as **non-production** demo data. Do not commit real credentials or PII into snapshots.
