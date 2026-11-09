# Date, tenure, and lifecycle metrics (WS-7)

## Architecture

All **reporting-date-dependent** Silver metrics use a single reference date:

| Mechanism | Value |
|-----------|--------|
| Python API | `db_config.get_as_of_date()` → `datetime.date` |
| Environment | `PULSEIQ_AS_OF_DATE` (ISO `YYYY-MM-DD`) |
| Default | **`2026-07-11`** — matches historical materialized ages on the authoritative DB |
| SQL embedding | `as_of_date_sql.duckdb_date_literal()` from validated date only |

**Not** replaced: event timestamps, trial length, deal cycle (create→close), activation 14-day windows.

## Account age

- **`account_age_days`** = `DATE_DIFF('day', created_date, as_of_date)` when `created_date <= as_of_date`; else **NULL**.
- **`account_age_bucket`**: existing thresholds for non-future rows; **`future`** when created after `as_of_date`.
- **`is_future_created`**: boolean flag; rows are retained.

## User tenure (two metrics)

| Column | Definition |
|--------|------------|
| **`user_tenure_days`** | `as_of_date − user.created_date` (unchanged semantic: **user** membership age) |
| **`account_tenure_days`** | `as_of_date − account.created_date` via `bronze_accounts` join; NULL if no account or future account |

`requirements.md` FR3 text conflated the name `user_tenure_days` with account creation — implementation keeps **both** columns explicitly.

## Deal metrics

| Column | Definition |
|--------|------------|
| **`deal_cycle_days`** | Closed deals: `closed_date − created_date` (unchanged) |
| **`deal_age_days`** | **Open pipeline only**: age from create to `as_of_date`; **NULL** if closed or future-created |
| **`is_future_created`** | Deal created after `as_of_date` |

**Compatibility:** Pre–WS-7 `deal_age_days` was populated for closed deals using “today”; dashboards that used it as “time in pipeline” for closed deals must use **`deal_cycle_days`** instead.

## User recency

- **`days_since_last_seen`** = diff from `last_seen_date` to `as_of_date` when `last_seen_date <= as_of_date`; else NULL.
- **`recency_bucket`**: `<7 days`, `7-29 days`, `30-89 days`, `90+ days`; **`future_last_seen`** when last seen after `as_of_date`; NULL when no last seen.
- Negative diffs are never mapped to active buckets.

## Future-dated records

Synthetic future creates are **kept**. Filter with `is_future_created = FALSE` or `created_date <= as_of_date` for as-of reporting. Distinguish:

- **Source dates** (row timestamps)
- **Event occurrence dates** (`EventDate`)
- **Reporting `as_of_date`**
- **Pipeline execution time** (operational only)

## Power BI

`data/dim_date.txt` uses **`ReportAsOfDate = DATE(2026, 7, 11)`** instead of `TODAY()`. Update this constant when changing `PULSEIQ_AS_OF_DATE`. Future: semantic-model parameter or config table.

## Activation / TTV

`gold_fact_advanced_activation` does **not** use `as_of_date`. Baseline: **21 / 120** activated (~**17.5%**), mean TTV **~9.9** days among activated accounts.

## Metric boundaries

Recency buckets use half-open day counts from `last_seen_date` to `as_of_date` (same CASE ordering as pre–WS-7, with future-last-seen guard).
