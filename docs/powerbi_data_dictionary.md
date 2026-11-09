# Power BI data dictionary (WS-15)

Source: `artifacts/ws15_powerbi_exports/` validated against `artifacts/ws15_final.duckdb` via `POWERBI_EXPORT_MANIFEST.json`.

**Reporting date:** 2026-07-11  
**Contexts:** `FULL_DATASET`, `AS_OF` (never mix on one KPI without a slicer).  
**Attribution:** Official metrics use `AttributionPopulation = OFFICIAL` (chronology-qualified).

## Dimensions

| File | Gold table | Grain | Key columns |
|------|------------|-------|-------------|
| `dim_accounts.csv` | `gold_dim_accounts` | Account | `AccountId`, `Segment`, `CreatedDate`, `IsFutureCreated` |
| `dim_users.csv` | `gold_dim_users` | User | `UserId`, `AccountId`, `CreatedDate` |
| `dim_geography.csv` | `gold_dim_geography` | Country | `CountryCode`, `Region`, `Market` |

## Facts (recommended for dashboard)

| File | Gold table | Grain | Purpose |
|------|------------|-------|---------|
| `fact_engagement_periodic.csv` | `gold_fact_engagement_periodic` | Context × period × entity type | DAU/WAU/MAU |
| `fact_feature_adoption_account.csv` | `gold_fact_feature_adoption_account` | Context × account × feature | Adoption flags, event counts |
| `fact_feature_adoption_user.csv` | `gold_fact_feature_adoption_user` | Context × user × feature | User adoption |
| `fact_feature_breadth_account.csv` | `gold_fact_feature_breadth_account` | Context × account | Distinct features adopted |
| `fact_feature_breadth_user.csv` | `gold_fact_feature_breadth_user` | Context × user | User breadth |
| `fact_retention_cohort.csv` | `gold_fact_retention_cohort` | Context × entity × window | D7/D14 exact-day |
| `fact_advanced_activation.csv` | `gold_fact_advanced_activation` | Account (full timeline) | FR10, TTV |
| `fact_activation_as_of.csv` | `gold_fact_activation_as_of` | Account × as-of eligibility | FR10 as-of |
| `fact_account_workflow_funnel.csv` | `gold_fact_account_workflow_funnel` | Context × workflow stage | Descriptive reach |
| `fact_segment_product_metrics.csv` | `gold_fact_segment_product_metrics` | Context × segment | SMB vs MID-MARKET |

## Row counts (WS-15 export run)

| Table | Rows |
|-------|-----:|
| `dim_accounts` | 120 |
| `dim_users` | 400 |
| `dim_geography` | (see manifest) |
| Others | See `POWERBI_EXPORT_MANIFEST.json` |

## Columns common to product facts

| Column | Meaning |
|--------|---------|
| `ReportContext` | `FULL_DATASET` or `AS_OF` |
| `ReportAsOfDate` | Cutoff for as-of logic |
| `AttributionPopulation` | `OFFICIAL` vs sensitivity populations |
| `EntityType` | `USER` or `ACCOUNT` where applicable |

## Not imported by default

| File | Reason |
|------|--------|
| `fact_qualified_product_events.csv` | Event-level; use for drill-through only |
| `fact_product_events.csv` | Raw gold events; prefer qualified models |
| `fact_deals.csv` | Deal ops; not WS-15 dashboard scope |

Regenerate manifest: `python scripts/generate_powerbi_export_manifest.py --export-dir artifacts/ws15_powerbi_exports --db-path artifacts/ws15_final.duckdb`.
