# PulseIQ — Product analytics coverage audit (WS-11)

**Phase 1 entry point.** Read-only audit of the Phase 0 warehouse. **Inspection database:** `artifacts/ws10_pulseiq.duckdb` (disposable pipeline output, `derived-fixture` geography, `ReportAsOfDate = 2026-07-11`). **Authoritative `product_analytics_light.db` was not used.**

Canonical activation definitions are unchanged — see [`metrics.md`](metrics.md).

---

## Executive summary

Phase 0 delivers a **reproducible medallion pipeline**, **event-grain facts** (60,552 non-test events), **account attribution with quarantine**, **seven canonical product events**, **JSON feature properties**, and **account-level advanced activation** (21/120 full-dataset; 0/15 as-of eligible). That foundation supports **volume, feature usage, segmentation, and account-level activation/TTV** case-study narratives.

**Gaps for classic product analytics:** no curated **global DAU/WAU/MAU**, **retention**, **funnels**, or **feature-adoption summary** Gold models; **1,151 event rows lack `UserId`** (1,141 SOURCE_VERIFIED); **415 events are quarantined** for account rollups; **104/120 accounts are future-created** relative to the default reporting date; event timestamps span **2026–2029** while many “as-of” dimensions assume **2026-07-11**.

**Recommendation:** WS-12+ should implement **P0** metrics on `gold_fact_product_events` with explicit **attribution policy**, **activity definition**, and **cohort maturity** rules — not dashboard-only logic in Power BI without documented grains.

---

## Current analytical data foundation

| Asset | Rows / scale | Role |
|-------|----------------|------|
| `gold_dim_accounts` | 120 | Account segments (SMB 83, MID-MARKET 37), tenure, geography join |
| `gold_dim_users` | 400 | User roles, recency, account link |
| `gold_fact_product_events` | 60,552 | One row per `EventSk`; identity + features |
| `gold_fact_product_events_aggregated` | 49,300 groups | Volume by date × event × feature × source `AccountId` |
| `gold_fact_advanced_activation` | 120 | FR10 activation + TTV (full dataset) |
| `gold_fact_activation_as_of` | 120 | Cohort maturity + as-of activation |
| `gold_fact_deals` | 6,443 | Deal lifecycle (duplicate `deal_id` groups documented) |
| `gold_dim_geography` | 7 (derived-fixture) | Not original Excel source |

**Pipeline validation:** latest successful run `artifacts/pipeline_runs/d0d0ace84e32.json` (row_counts and DQ passed).

---

## A. Identity and attribution

### Verified counts (disposable DB, 2026-11 audit)

| `account_resolution_status` | Events |
|----------------------------|-------:|
| SOURCE_VERIFIED | **59,911** |
| ENRICHED | **226** |
| QUARANTINED | **415** |
| **Total** | **60,552** |

Matches WS-9 contracts and [`orphan_events.md`](orphan_events.md).

### Account-level activity

| Measure | Value | Assessment |
|---------|------:|------------|
| Distinct source `AccountId` (verified events) | 120 | **Reliable** for conservative account metrics when filtered to SOURCE_VERIFIED |
| Distinct `AccountIdResolved` | 120 | ENRICHED adds resolved accounts without changing distinct account count on this dataset |
| Events with null source `AccountId` | 641 | Excluded from source-account rollups; 415 quarantined, 226 enriched |
| Quarantined rows | 415 | **Exclude** from official account metrics |

**Analytical populations**

1. **Conservative (official):** `AccountResolutionStatus = 'SOURCE_VERIFIED'` and **`AccountId`**. Use for activation-aligned and executive metrics.
2. **Expanded sensitivity:** add `ENRICHED` with **`AccountIdResolved`**. +226 events; material for attribution sensitivity, not baseline KPIs.

Do **not** include QUARANTINED or ENRICHED in official activation (unchanged FR10 uses source `AccountId` only).

### User-level activity

| Measure | Value | Assessment |
|---------|------:|------------|
| `gold_dim_users` | 400 | Full user dimension |
| Distinct `UserId` in events (non-null) | 400 | All synthetic users emit events |
| Events with **null `UserId`** | **1,151** | **1,141** SOURCE_VERIFIED — user-level numerators must filter `UserId IS NOT NULL` |
| Grain | `EventSk` unique | Joins to dims do not multiply events |

**Cohort analysis:** Account and user **created dates** exist on dims; user–account link is mostly reliable via `bronze_users`, but **nine users** have weak account linkage (per `orphan_events.md`). Account cohorts are **more reliable** than user cohorts at small n (120 accounts).

---

## B. Event taxonomy and behaviour

Seven **normalized** names (verified event counts × 400 users × 120 accounts each):

| `EventNameNormalized` | Rows | Product interpretation |
|----------------------|-----:|------------------------|
| `enable_automation` | 12,159 | Automation / workflow configuration |
| `log_activity` | 12,135 | CRM activity logging |
| `move_deal_stage` | 12,103 | Pipeline stage progression |
| `create_deal` | 12,053 | Deal creation |
| `view_dashboard` | 4,102 | Dashboard engagement |
| `login` | 4,003 | Authentication / session (incl. aliases) |
| `invite_user` | 3,997 | Team invite / onboarding signal |

**Categories** (Silver rule on normalized name): PIPELINE 24,156; AUTOMATION 12,159; ACTIVITY 12,135; OTHER 8,099; AUTH 4,003.

**Features** (`FeatureName`, SOURCE_VERIFIED): dashboard 15,084; automation 15,046; pipeline 15,044; deal 14,737 — aligned with JSON `feature_name` (see [`feature_adoption.md`](feature_adoption.md)).

**Deal context:** `HasDealContext` / `deal_id` on events supports pipeline activation logic; not equivalent to “meaningful product value” alone.

**First event per account (SOURCE_VERIFIED, by calendar day):** `log_activity` 211, `move_deal_stage` 201, `enable_automation` 191, `create_deal` 177, `invite_user` 80, `login` 64, `view_dashboard` 59. **Data-supported finding:** the simulated corpus does **not** follow a clean “signup → login → dashboard” ordering; funnels are **analytical constructs**, not observed onboarding truth.

**Clarification required:** None for the seven canonical names (documented in [`event_taxonomy.md`](event_taxonomy.md)). `log_activity` breadth (calls/emails/notes) is not subdivided in events.

---

## C. Time and cohort considerations

| Dimension | Range / note |
|-----------|----------------|
| `EventDate` | 2026-01-01 → 2029-12-31 |
| Account `CreatedDate` | 2026-01-03 → 2029-12-22 |
| Default `ReportAsOfDate` | **2026-07-11** |
| `IsFutureCreated` accounts | **104 / 120** |
| As-of **eligible** accounts (window complete) | **15** (0 activated as-of) |

**Full-dataset vs as-of**

- **Metric A** activation **21/120 = 17.5%** uses the **entire synthetic timeline** — accounts created in 2027–2029 contribute. It is **not** the July 11, 2026 activation rate.
- **Metric B** **0/15** is the correct **historical as-of** eligible rate at default reporting date.
- Analyses without `IsEligibleAsOf`, `is_future_created`, or explicit date filters **overstate maturity** for as-of storytelling.

**Retention / Dn metrics** require:

- Cohort anchor (`CreatedDate` or first activity date)
- Activity definition and attribution filter
- **Right-censoring:** exclude or flag cohorts whose observation window is incomplete at `ReportAsOfDate`

**Probe (calendar exact day, SOURCE_VERIFIED, all accounts):** share with any event on account create day **4/120**, day **+7: 8/120**, day **+14: 10/120** — illustrates sensitivity to window definition; rolling “active within 7 days” will differ.

---

## Metric-family feasibility matrix

| Family | Representative metrics | Status |
|--------|------------------------|--------|
| **Engagement** | User DAU/WAU/MAU; Account DAU/WAU/MAU | **IMPLEMENTABLE** (detail fact); not in Gold today |
| **Activation funnel** | Account FR10 activation; as-of eligible | **IMPLEMENTED** (account only) |
| **Activation funnel** | User activation; stepwise onboarding funnel | **PROPOSED** / **NOT_FEASIBLE** as causal journey |
| **Retention** | D1/D7/D14 user or account retention | **IMPLEMENTABLE_WITH_CAVEATS** |
| **Retention** | Rolling weekly/monthly retention | **IMPLEMENTABLE_WITH_CAVEATS** |
| **Feature adoption** | Distinct user/account per feature; first use | **IMPLEMENTABLE** (SQL on detail) |
| **Feature adoption** | Curated adoption Gold table | **PARTIAL** (agg volume only) |
| **Funnels** | Ordered multi-step conversion | **IMPLEMENTABLE_WITH_CAVEATS** |
| **Segmentation** | Segment, tenure, feature mix | **IMPLEMENTABLE** |
| **Segmentation** | Rich geography / firmographics | **PARTIAL** (derived geography only) |
| **Risk / correlation** | Early feature use → later engagement | **Analytical hypothesis** only |

Detail: [`product_analytics_metric_specification.md`](product_analytics_metric_specification.md).

---

## Data limitations

- Synthetic data; **no** experiments, revenue, churn, NPS, or support tickets.
- **625** null `event_id`, **653** null `account_id` at raw (manifest); Silver excludes test events only.
- **35** duplicate `deal_id` row groups (single account each) — do not dedupe silently.
- **Missing `raw_geography.xlsx`** — `derived-fixture` is **not** original source geography.
- **Aggregated `UniqueUsers`** is per-group only — **not** global DAU.
- **Future-dated** entities dominate default as-of slice (104 accounts).

---

## Product questions — what the data can support

| Question | Verdict |
|----------|---------|
| Which features see the most **event volume**? | **Data-supported** (`FeatureName` / event counts) |
| Which features reach the most **distinct users/accounts**? | **Data-supported** (detail `COUNT DISTINCT`, attribution policy) |
| Broad vs narrow feature use per account? | **Data-supported** (feature breadth per account) |
| Account **activation** and **TTV** (FR10)? | **Data-supported** (implemented metrics) |
| **As-of** activation for mature cohorts? | **Data-supported** (metric B; often 0% at default date) |
| Global **DAU/WAU/MAU**? | **Not currently measurable** in Gold; **implementable** from detail |
| **Onboarding funnel** drop-off by login → dashboard → deal? | **Analytical hypothesis** only — event order does not match classic onboarding |
| **User activation** in 14-day window? | **Not currently measurable** (no definition implemented) |
| **Retention** D7/D14? | **Answer with caveats** (small n, maturity, activity definition) |
| Early feature use **causes** better engagement? | **Not currently measurable** (no causal design) |
| Geography-driven engagement differences? | **Limited** (7-country fixture; not production geography) |
| Which accounts are **at risk** (no recent activity)? | **Data-supported** via user recency + account event recency (to be modeled) |

---

## Questions that cannot currently be answered reliably

- Official **user-level** activation rate comparable to FR10.
- **Experiment lift** or causal impact of product changes.
- **Revenue-weighted** value or expansion/contraction.
- **Global DAU** from aggregated Gold without new SQL.
- **Production-grade** geo/region performance (missing Excel source).

---

## Recommended next steps (WS-12+)

See roadmap in [`product_analytics_metric_specification.md`](product_analytics_metric_specification.md) § Roadmap. WS-11 does **not** implement metrics.

---

## Audit method

- Documents: README, CHANGES, metric contracts, metrics, provenance, feature adoption, event taxonomy, orphan events, date/tenure, RUNBOOK, pipeline architecture.
- Schemas: `sql/gold_table_schemas.py`, Gold/Silver SQL headers and joins.
- Tests: WS-9 data-quality and export contracts (reference expectations).
- Data: read-only DuckDB on disposable artifact; pipeline report `d0d0ace84e32.json`.
- **No** changes to transformation SQL, snapshots, authoritative DB, tests, or pipeline code.
