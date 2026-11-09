# Pipeline architecture (WS-10)

## Layers

```text
data/source_snapshot (Parquet + MANIFEST.json)
        │
        ▼ validate_raw_snapshot.py
        ▼ load_raw.py → raw__*
        ▼ bronze_*.py → bronze_*
        ▼ silver_*.py → silver_*
        ▼ gold_*.py → gold_*
        ▼ export_gold_to_csv.py → CSV
        ▼ pipeline DQ + export validation
```

## Execution dependency graph

| Stage | Depends on |
|-------|------------|
| `load_raw` | Valid snapshots |
| `bronze_*` | `raw__*` |
| `geography` | `raw__accounts` (fixture) or Excel (source) |
| `silver_geography` | `bronze_geography` (source mode only) |
| `silver_accounts` | `bronze_accounts`, `bronze_geography` (joins) |
| `silver_users` | `bronze_users`, `bronze_accounts` |
| `silver_deals` | `bronze_deals` |
| `silver_product_events` | `bronze_product_events`, `bronze_accounts`, `raw__deals`, `silver_users` |
| `gold_dim_accounts` | `silver_accounts` |
| `gold_dim_users` | `silver_users` |
| `gold_dim_geography` | `silver_geography` |
| `gold_fact_deals` | `silver_deals` |
| `gold_fact_product_events` | `silver_product_events` |
| `gold_fact_product_events_aggregated` | `silver_product_events` |
| `gold_fact_advanced_activation` | `gold_dim_accounts`, `gold_fact_product_events`, `gold_fact_deals` |
| `gold_fact_activation_as_of` | `gold_dim_accounts`, `gold_fact_advanced_activation` |

Orchestrator entry: `run_pipeline.py` → `sql/pipeline/runner.py`.

## Database configuration

- Path: `PULSEIQ_DB_PATH` / `--db-path` (required for real runs)
- Safety: `sql/pipeline/safety.py` blocks `product_analytics_light.db` unless explicitly allowed
- Transformations use `sql/db_config.py` (`connect_duckdb`, `get_as_of_date`)

## Reporting date propagation

`PULSEIQ_AS_OF_DATE` / `--as-of-date` (CLI overrides env) feeds `get_as_of_date()` in Silver tenure/age scripts and `gold_fact_activation_as_of`.

Default: **2026-07-11**.

## Geography limitation

Original `raw_geography.xlsx` is not versioned. **`derived-fixture`** builds a minimal reference table from account countries for reproducible CI and clone-from-Git workflows.

## Data quality validation

Pipeline gate: `sql/pipeline/dq_validation.py` (subset of WS-9 contracts).

Full developer suite: `pytest tests/` including `test_data_quality_contracts.py`.

## Export architecture

- Script: `sql/gold/export_gold_to_csv.py`
- Schema map: `sql/gold_table_schemas.py` → `exports/gold_csv` filenames
- Default pipeline output: `artifacts/gold_csv` (not committed `exports/gold_csv` unless you pass that path explicitly)
- Post-export gate: `sql/pipeline/export_validation.py`
