# PulseIQ pipeline runbook (WS-10)

## Prerequisites

- Python 3.10+
- Git clone of PulseIQ with `data/source_snapshot/` present
- Install dependencies: `pip install -r requirements.txt`
- Optional geography source: `sql/data/raw_geography.xlsx` (not in repo; use `derived-fixture` mode otherwise)

## Environment

| Variable | Purpose |
|----------|---------|
| `PULSEIQ_DB_PATH` | Target DuckDB (non-authoritative) |
| `PULSEIQ_AS_OF_DATE` | Reporting date `YYYY-MM-DD` (CLI `--as-of-date` wins) |
| `PULSEIQ_EXPORT_DIR` | CSV output directory |
| `PULSEIQ_ALLOW_AUTHORITATIVE_DB` | `1` to allow writes to `product_analytics_light.db` |
| `PULSEIQ_EXPORT_TABLES` | Comma subset for partial export (exporter only) |

**Never** point the pipeline at `product_analytics_light.db` without an explicit override.

## Validate snapshot only

```powershell
python sql/validate_raw_snapshot.py
```

## Full pipeline

```powershell
python run_pipeline.py `
  --db-path ".\artifacts\pulseiq.duckdb" `
  --as-of-date "2026-07-11" `
  --geography-mode "derived-fixture" `
  --export-dir ".\artifacts\gold_csv"
```

Exit code `0` = success; `1` = stage/DQ/export failure; `2` = CLI or safety error.

WS-12 adds Gold exports: `fact_engagement_periodic.csv`, `fact_feature_adoption_*.csv`, `fact_feature_breadth_*.csv`, `fact_product_activity_recency_*.csv`.

## Dry run

```powershell
python run_pipeline.py --dry-run --geography-mode derived-fixture
```

Prints stage order without loading or transforming data.

## Geography modes

- **`derived-fixture`** (default): Deterministic bronze/silver geography from `raw__accounts.country_code`. Does **not** reproduce the missing Excel source.
- **`source`**: Runs `bronze_geography.py` / `silver_geography.py`. **Fails** if `sql/data/raw_geography.xlsx` is absent.

## Tests

```powershell
python -m pytest tests/ -q
```

Orchestration tests: `tests/test_pipeline_orchestration.py` (temp DB only).

## Execution report

JSON report per run: `artifacts/pipeline_runs/<run_id>.json`

## Troubleshooting

| Symptom | Action |
|---------|--------|
| `Database path is required` | Pass `--db-path` or set `PULSEIQ_DB_PATH` |
| `Refusing to modify authoritative` | Use `artifacts\pulseiq.duckdb` or similar |
| Geography source failure | Switch to `--geography-mode derived-fixture` |
| DQ stage failed | See report `dq.errors`; run `pytest tests/test_data_quality_contracts.py` |
| Partial CSV export | Full pipeline requires all Gold tables; check exporter logs for "Skipped" |
