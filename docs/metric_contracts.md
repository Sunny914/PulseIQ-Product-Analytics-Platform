# PulseIQ metric & data-quality contracts (WS-9)

Canonical narrative for activation and as-of metrics lives in [`metrics.md`](metrics.md). This document indexes **implemented** warehouse metrics, their verification tests, and explicit non-implementations.

**Default reporting date:** `2026-07-11` (`PULSEIQ_AS_OF_DATE` / `get_as_of_date()`).

---

## Test coverage map

| Layer | Primary tests |
|-------|----------------|
| Raw snapshot | `tests/test_raw_snapshot.py`, `tests/test_data_quality_contracts.py` |
| Event identity | `tests/test_event_identity.py` |
| Event taxonomy | `tests/test_event_normalization.py` |
| Account attribution | `tests/test_orphan_quarantine.py` |
| Feature properties | `tests/test_feature_properties.py` |
| Date / tenure | `tests/test_as_of_date.py` |
| Activation / as-of | `tests/test_activation_as_of.py`, `tests/test_data_quality_contracts.py` |
| Gold schema / agg | `tests/test_gold_aggregated_schema.py` |
| CSV export | `tests/test_export_contracts.py` |
| Cross-layer | `tests/test_data_quality_contracts.py` |

---

## IMPLEMENTED METRICS

### 1. Full-dataset activation rate

| Field | Value |
|-------|--------|
| **Meaning** | Share of all accounts meeting FR10 advanced activation |
| **Grain** | Account |
| **Numerator** | `IsActivated = TRUE` (`gold_fact_advanced_activation`) |
| **Denominator** | All accounts (120) |
| **Window** | Inclusive 14 days post `CreatedDate` |
| **Reporting date** | Not used |
| **Attribution** | Source `AccountId`; deal-context events; deal create in window |
| **Exclusions** | Orphan/quarantine events (no source `AccountId`) |
| **Reference** | **21 / 120 = 17.5%** |
| **Tests** | `test_data_quality_contracts`, `test_activation_as_of` |
| **Limitations** | Synthetic cohorts; not as-of historical rate |

### 2. As-of eligible activation rate

| Field | Value |
|-------|--------|
| **Meaning** | Activation among accounts with complete 14-day window by `ReportAsOfDate` |
| **Grain** | Account (`gold_fact_activation_as_of`) |
| **Numerator** | `IsEligibleAsOf AND IsActivatedAsOf` |
| **Denominator** | `IsEligibleAsOf` only (excludes future / immature) |
| **Reference** | **0 / 15 = 0%** at default as-of |
| **Tests** | `test_activation_as_of`, `test_data_quality_contracts` |

### 3. Full-dataset TTV (`TimeToValueDays` / `TimeToValueDaysFullDataset`)

| Field | Value |
|-------|--------|
| **Formula** | `DATE_DIFF(day, CreatedDate, GREATEST(first core, first deal))` |
| **Population** | Activated accounts only |
| **Reference** | Mean **~9.904762**, median **10** (n=21) |
| **Tests** | `test_activation_as_of`, `test_data_quality_contracts` |

### 4. As-of TTV (`TimeToValueDaysAsOf`)

| Field | Value |
|-------|--------|
| **Population** | `IsEligibleAsOf AND IsActivatedAsOf` only; else NULL |
| **Reference** | All NULL (0 eligible activated) |
| **Tests** | `test_activation_as_of`, `test_export_contracts` |

### 5. Account age (`account_age_days`)

| **Source** | `silver_accounts` / `gold_dim_accounts.AccountAgeDays` |
| **Formula** | `DATE_DIFF(day, created_date, as_of_date)`; NULL if future-created |
| **Tests** | `test_as_of_date` |

### 6. User tenure (`user_tenure_days`)

| **Formula** | `as_of_date − user.created_date` |
| **Tests** | `test_as_of_date` |

### 7. Account tenure on user (`account_tenure_days` / `AccountTenureDays`)

| **Formula** | `as_of_date − account.created_date` via join |
| **Tests** | `test_as_of_date` |

### 8. Deal age (`deal_age_days`)

| **Formula** | Open deals only: create → `as_of_date`; NULL if closed/future |
| **Tests** | `test_as_of_date` |

### 9. Deal cycle (`deal_cycle_days`)

| **Formula** | `closed_date − created_date` when closed |
| **Tests** | `test_as_of_date` |

### 10. User recency (`days_since_last_seen`, `recency_bucket`)

| **Formula** | `as_of_date − last_seen_date`; `future_last_seen` when last seen after as-of |
| **Tests** | `test_as_of_date` |

### 11. Event volume

| **Grain** | Event (`event_sk`) / aggregated groups |
| **Reference detail** | **60,552** non-test events |
| **Agg reconcile** | `SUM(EventCount) = 60,552` |
| **Tests** | `test_data_quality_contracts`, `test_gold_aggregated_schema` |

### 12. Feature usage (volume)

| **Fields** | `FeatureName`, `EventSource`, `EventCount` in agg |
| **Tests** | `test_feature_properties` |

### 13. Distinct-user feature adoption (definition)

| **Definition** | `COUNT(DISTINCT UserId)` for qualifying events — **not** event row count |
| **Implemented in Gold** | `UniqueUsers` **per aggregated group only** |
| **Limitation** | **Do not** sum `UniqueUsers` across groups for global DAU |
| **Tests** | Documented; partial via `test_gold_aggregated_schema` |

---

## WS-12 IMPLEMENTED PRODUCT METRICS

| Metric | Gold table | Tests |
|--------|------------|-------|
| User DAU / WAU / MAU | `gold_fact_engagement_periodic` | `test_ws12_product_analytics` |
| Account DAU / WAU / MAU | same | same |
| Account feature adoption | `gold_fact_feature_adoption_account` | same |
| User feature adoption | `gold_fact_feature_adoption_user` | same |
| Feature adoption by month | `gold_fact_feature_adoption_by_period` | same |
| Feature breadth (account/user) | `gold_fact_feature_breadth_*` | same |
| Product activity recency | `gold_fact_product_activity_recency_*` | same |
| Qualified events + chronology | `gold_fact_qualified_product_events` | `test_ws13_chronology_retention` |
| Retention D7/D14 | `gold_fact_retention_cohort` | same |
| Workflow funnel (descriptive) | `gold_fact_account_workflow_funnel` | same |
| Segment product summary | `gold_fact_segment_product_metrics` | same |

**Contexts:** `ReportContext` = `FULL_DATASET` \| `AS_OF` (`EventDate <= ReportAsOfDate` **and** entity `CreatedDate <= ReportAsOfDate` for AS_OF populations).  
**Chronology:** Official metrics require `EventDate >= entity CreatedDate` (see `docs/chronology_integrity_audit.md`).  
**Attribution:** `OFFICIAL` and `SENSITIVITY` populations per `sql/product_analytics_sql.py`.

---

## PARTIALLY IMPLEMENTED METRICS

| Metric | Gap |
|--------|-----|
| Rolling 7/28-day engagement (alternate to calendar week/month) | Not materialized; calendar week/month in WS-12 |
| Segment activation dashboards | Data exists; no curated Gold summary table |
| Enriched-attribution activation | Sensitivity only (WS-8 audit); not official baseline |

---

## PROPOSED METRICS (not implemented)

- User-level 14-day activation
- Cohort retention / funnel conversion
- Statistically validated experiment lift
- Geography-enriched dims at full parity (missing `raw_geography.xlsx`)
- Revenue-weighted TTV

---

## Data-quality contracts (reference)

| Reconciliation | Expected |
|----------------|----------|
| Raw product events | 61,747 |
| Bronze product events | 61,747 |
| Silver product events | 60,552 (excludes 1,195 test) |
| Attribution partition | 59,911 + 226 + 415 = 60,552 |
| Gold detail events | 60,552 |
| Duplicate `deal_id` groups | 35 (single account each — documented in MANIFEST) |
| Known raw nulls | 625 `event_id`, 653 `account_id` (manifest) |

---

## Known exceptions

- **Geography:** Test fixture stubs `bronze_geography` / `silver_geography` when Excel missing — not production source.
- **Authoritative DB** may lag repo code until ETL re-run.
- **17.5% activation** must not be labeled as July 2026 as-of performance (see `metrics.md`).
