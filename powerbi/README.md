# PulseIQ Power BI handoff (WS-15)

**Status:** Ready-to-import CSVs + semantic specification. **No `.pbix` / `.pbip` is committed** — Power BI Desktop was not available in the build environment for validation.

## Quick start

1. Generate exports (from repo root):

```powershell
python run_pipeline.py `
  --db-path ".\artifacts\pulseiq.duckdb" `
  --export-dir ".\artifacts\ws15_powerbi_exports" `
  --as-of-date "2026-07-11" `
  --geography-mode derived-fixture
```

2. Open **Power BI Desktop** → **Get data** → **Text/CSV** → folder `artifacts/ws15_powerbi_exports`.
3. Set the **ExportFolderPath** parameter (see `Parameter.ExportFolderPath.pq`).
4. Follow [`docs/powerbi_setup.md`](../docs/powerbi_setup.md) for relationships and pages.
5. Import measures from [`docs/powerbi_measure_catalog.md`](../docs/powerbi_measure_catalog.md).

**Synthetic data only** — not real customers or production KPIs.
