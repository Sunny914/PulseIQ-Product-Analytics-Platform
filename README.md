# PulseIQ — Synthetic B2B CRM product analytics

**One line:** Reproducible medallion pipeline + metric contracts + Gold product analytics + Power BI handoff for a **fictional** SaaS CRM portfolio.

> **Synthetic data only.** PulseIQ does not describe real customers, revenue, deployments, or experiment results. All KPIs are illustrative.

---

## Problem and objective

Show how a product analytics team turns raw product events into **defensible** activation, engagement, feature adoption, retention, funnel reach, and segmentation — with explicit data-quality and reporting-context rules recruiters can question in interviews.

---

## Key capabilities

| Area | What is implemented |
|------|---------------------|
| Data engineering | Bronze → Silver → Gold (DuckDB), snapshot load, orchestrated `run_pipeline.py` |
| Data quality | Contracts, validation, SOURCE_VERIFIED / ENRICHED / QUARANTINED |
| Product metrics | DAU/WAU/MAU, adoption, breadth, exact-day D7/D14 retention, FR10 activation, descriptive funnel |
| Chronology | Official analytics on `gold_fact_qualified_product_events` |
| Contexts | **FULL_DATASET** vs **AS_OF 2026-07-11** (never mix without a slicer) |
| Decision docs | Opportunities, PRDs, roadmap (WS-14) |
| Portfolio (WS-15) | Case study, demo script, Power BI CSV manifest, measure catalog |

---

## Major findings (as-of 2026-07-11, official)

| Theme | Result | Notes |
|-------|--------|--------|
| Feature adoption | Up to **15/15** account adopters on core features | Mature as-of cohort |
| FR10 activation | **0 / 15** eligible as-of | Separate from engagement |
| Full-dataset activation | **21 / 120 (17.5%)**, mean TTV **~9.9 days** | Not the as-of rate |
| Account retention D7/D14 | **0 / 15** | Exact-day, not rolling |
| User retention D7 | **2 / 56 (~3.6%)** | |
| Funnel | High **deal** stage reach | Descriptive reach only |
| Sample size | **16** accounts created by as-of date | Show on segment views |

Details: [`docs/product_insights_and_recommendations.md`](docs/product_insights_and_recommendations.md) · Case study: [`docs/pulseiq_case_study.md`](docs/pulseiq_case_study.md)

---

## Dashboard status

| Item | Status |
|------|--------|
| Validated `.pbix` / `.pbip` in repo | **No** — Power BI Desktop was not available to validate a report file |
| Gold CSV exports + manifest | **Yes** — `artifacts/ws15_powerbi_exports/` |
| Setup guide + DAX catalog | [`docs/powerbi_setup.md`](docs/powerbi_setup.md), [`docs/powerbi_measure_catalog.md`](docs/powerbi_measure_catalog.md) |
| Parameterised M samples | [`powerbi/`](powerbi/) |

Build the six-page report locally (Executive, Engagement, Adoption, Retention, Activation & workflow, Segments). Capture screenshots only from a real report — none are shipped as fake renders.

**Demo script:** [`docs/demo_walkthrough.md`](docs/demo_walkthrough.md)

---

## Architecture

Medallion pipeline in DuckDB; exports feed Power BI. Diagram source: [`docs/diagrams/pulseiq_architecture.mmd`](docs/diagrams/pulseiq_architecture.mmd).

```text
Snapshots → Bronze → Silver → Gold → CSV + DuckDB → Power BI (import)
```

Deep dive: [`docs/pipeline_architecture.md`](docs/pipeline_architecture.md) · [`docs/RUNBOOK.md`](docs/RUNBOOK.md)

---

## Technology stack

| Layer | Tools |
|-------|--------|
| Database | DuckDB |
| Transform | SQL + Python |
| Tests | pytest |
| BI | Power BI Desktop (local build) |
| Docs | Markdown |

---

## Repository structure (high level)

| Path | Purpose |
|------|---------|
| `data/source_snapshot/` | Versioned synthetic sources |
| `sql/bronze`, `sql/silver`, `sql/gold` | Layer transforms |
| `run_pipeline.py` | End-to-end orchestration |
| `tests/` | Contracts and regression tests |
| `docs/` | Metrics, audits, case study, Power BI docs |
| `artifacts/` | Disposable DBs and WS-15 exports (not authoritative DB) |
| `CHANGES.md` | Full workstream history WS-1–WS-15 |

---

## Setup and reproducibility

```powershell
pip install -r requirements.txt

# Disposable DB + Power BI exports (does not touch product_analytics_light.db)
python run_pipeline.py `
  --db-path ".\artifacts\ws15_final.duckdb" `
  --export-dir ".\artifacts\ws15_powerbi_exports" `
  --as-of-date "2026-07-11" `
  --geography-mode derived-fixture

python scripts/generate_powerbi_export_manifest.py `
  --export-dir ".\artifacts\ws15_powerbi_exports" `
  --db-path ".\artifacts\ws15_final.duckdb"

python -m pytest tests/ -q
```

Metric definitions: [`docs/metrics.md`](docs/metrics.md), [`docs/metric_contracts.md`](docs/metric_contracts.md), [`docs/product_analytics_metric_specification.md`](docs/product_analytics_metric_specification.md)

---

## Limitations (read before interviewing)

- Synthetic CRM; no production or causal claims.
- Pre-creation events excluded from **official** conclusions.
- **FR10 activation ≠** general qualified engagement.
- Retention is **exact-day** D7/D14 — not labelled as rolling retention.
- Workflow funnel is **reach**, not sequential conversion.
- As-of segment comparisons are **underpowered** (e.g. MID-MARKET **n = 2**).

---

## Development status

**WS-15 complete — PulseIQ development stops here.** Implementation log: [`CHANGES.md`](CHANGES.md).
