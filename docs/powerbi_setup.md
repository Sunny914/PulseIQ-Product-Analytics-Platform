# Power BI setup (WS-15)

## Environment check

| Item | Status |
|------|--------|
| Power BI Desktop on build machine | **Not detected** — no validated `.pbix` / `.pbip` in repo |
| Gold CSV exports | **Yes** — `artifacts/ws15_powerbi_exports/` |
| Manifest | `POWERBI_EXPORT_MANIFEST.json` |

## 1. Refresh exports

```powershell
python run_pipeline.py --db-path ".\artifacts\ws15_final.duckdb" `
  --export-dir ".\artifacts\ws15_powerbi_exports" `
  --as-of-date "2026-07-11" --geography-mode derived-fixture

python scripts/generate_powerbi_export_manifest.py `
  --export-dir ".\artifacts\ws15_powerbi_exports" `
  --db-path ".\artifacts\ws15_final.duckdb"
```

## 2. Import tables (recommended subset)

| CSV | Role |
|-----|------|
| `dim_accounts.csv` | Account dimension |
| `dim_users.csv` | User dimension |
| `fact_engagement_periodic.csv` | DAU/WAU/MAU |
| `fact_feature_adoption_account.csv` | Account feature adoption |
| `fact_feature_adoption_user.csv` | User feature adoption |
| `fact_feature_breadth_account.csv` | Breadth |
| `fact_retention_cohort.csv` | D7/D14 retention |
| `fact_advanced_activation.csv` | FR10 full-dataset |
| `fact_activation_as_of.csv` | FR10 as-of |
| `fact_account_workflow_funnel.csv` | Descriptive reach |
| `fact_segment_product_metrics.csv` | SMB / MID-MARKET |

Use `Parameter.ExportFolderPath.pq` or Power BI **Parameters** for folder path.

## 3. Relationships (star-ish)

| From | To | Cardinality | Notes |
|------|-----|-------------|--------|
| `fact_feature_adoption_account[AccountId]` | `dim_accounts[AccountId]` | M:1 | Filter direction single |
| `fact_feature_adoption_user[UserId]` | `dim_users[UserId]` | M:1 | |
| `fact_feature_breadth_account[AccountId]` | `dim_accounts[AccountId]` | M:1 | |
| `fact_advanced_activation[AccountId]` | `dim_accounts[AccountId]` | M:1 | |
| `fact_activation_as_of[AccountId]` | `dim_accounts[AccountId]` | M:1 | |

**Do not** relate engagement periodic to accounts on `AccountId` (aggregated grain). **Do not** sum `ActiveEntityCount` across contexts.

## 4. Report pages (build checklist)

1. **Executive overview** — context slicer, disclaimers, AS_OF KPIs only on AS_OF page.
2. **Engagement** — user vs account visuals separate; filter `ReportContext`.
3. **Feature adoption** — adoption vs `FeatureEventCount`.
4. **Retention** — show `EligibleEntities`, `RetainedEntities`, exact-day note.
5. **Activation & workflow** — FR10 separate from engagement; funnel disclaimer.
6. **Segments** — show `EligibleAccounts` per segment; small-sample warning.

## 5. Theme

- Canvas: charcoal `#1E1E2E` or white `#FAFAFA`.
- Accent: teal `#2BB3A3` or blue `#3B82F6`.
- Header font: Segoe UI Semibold; body Segoe UI.
- Place synthetic disclaimer text box on every page.

## 6. Screenshots

Capture from Power BI after build; save under `docs/images/` (not committed as fake renders).
