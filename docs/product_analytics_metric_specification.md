# PulseIQ — Product analytics metric specification (WS-11)

**Status:** Living specification. WS-12 implemented P0 metrics below; statuses updated in place.

**Canonical implemented metrics** (activation, TTV, tenure, recency, event volume): defined in [`metrics.md`](metrics.md) and [`metric_contracts.md`](metric_contracts.md). This document **references** those definitions and specifies **candidate** Phase 1 metrics.

**Default reporting date:** `2026-07-11` unless stated otherwise.

**Attribution policies**

| Code | Filter | Field |
|------|--------|-------|
| **OFFICIAL** | `AccountResolutionStatus = 'SOURCE_VERIFIED'` | `AccountId` |
| **SENSITIVITY** | `IN ('SOURCE_VERIFIED','ENRICHED')` | `AccountIdResolved` |
| **USER_OFFICIAL** | OFFICIAL + `UserId IS NOT NULL` | `UserId` |

---

## Roadmap summary

| Priority | Metrics | Rationale |
|----------|---------|-----------|
| **P0** | User/account DAU/WAU/MAU; feature adoption (distinct user/account); feature breadth; activity recency | High case-study value; data-ready on detail fact |
| **P1** | D7/D14 retention (user + account); funnel step conversion (explicit non-causal); segment engagement | Needs maturity filters and documented activity rules |
| **P2** | Causal / predictive models; geo performance at source parity; sessionization; multi-touch attribution | Instrumentation or dimensions missing |

---

## A. Engagement metrics

### A1. User DAU

| Field | Specification |
|-------|----------------|
| **Business purpose** | Daily active **users** using the product |
| **Status** | **IMPLEMENTED** (`gold_fact_engagement_periodic`, `PeriodType='DAY'`) |
| **Grain** | Calendar day × EntityType × AttributionPopulation × ReportContext |
| **Numerator** | `COUNT(DISTINCT UserId)` |
| **Denominator** | N/A (level metric) |
| **Activity** | Default: any non-test product event with USER_OFFICIAL filter. Variant: exclude `EventNameNormalized = 'login'` for “productive DAU” (document choice) |
| **Sources** | `gold_fact_product_events` (`EventDate`, `UserId`, `EventNameNormalized`, attribution columns) |
| **Attribution** | OFFICIAL recommended |
| **Window** | Single calendar `EventDate` |
| **Maturity** | For as-of reporting, exclude events with `EventDate > ReportAsOfDate` |
| **Limitations** | 1,141 verified rows lack `UserId`; aggregated Gold **cannot** supply global DAU |
| **Validation** | Distinct count equals manual spot-check; not equal to `SUM(UniqueUsers)` from agg |

### A2. User WAU / MAU

Calendar **WEEK** (ISO week, Monday start) and **MONTH** on `EventDate`. **Status:** **IMPLEMENTED** (`PeriodType` WEEK \| MONTH). **WS-12 decision:** calendar boundaries (not rolling 7/28) — documented here because WS-11 allowed either.

### A3. Account DAU / WAU / MAU

| Field | Specification |
|-------|----------------|
| **Grain** | Calendar day (or window) × account |
| **Numerator** | `COUNT(DISTINCT AccountId)` under OFFICIAL |
| **Activity** | Same event rules as A1; **separate metric** from user engagement — do not blend |
| **Status** | **IMPLEMENTED** (same table, `EntityType='ACCOUNT'`) |
| **Validation** | `test_ws12_product_analytics`; ActiveEntityCount ≤ 120 |

---

## B. Activation and funnel metrics

### B1. Account advanced activation rate (full dataset)

| Field | Specification |
|-------|----------------|
| **Status** | **IMPLEMENTED** |
| **Reference** | **21 / 120 = 17.5%** |
| **Definition** | See [`metrics.md`](metrics.md) — FR10, 14-day window, core deal-context event + deal create |
| **Do not relabel** | Not the 2026-07-11 as-of rate |

### B2. Account as-of eligible activation rate

| Field | Specification |
|-------|----------------|
| **Status** | **IMPLEMENTED** |
| **Reference** | **0 / 15 = 0%** at default `ReportAsOfDate` |
| **Definition** | [`metrics.md`](metrics.md) metric B |

### B3. Account time to value (full / as-of)

| Field | Specification |
|-------|----------------|
| **Status** | **IMPLEMENTED** |
| **Reference mean TTV** | ~**9.904762** days (activated, full dataset) |
| **Columns** | `TimeToValueDays`, `TimeToValueDaysFullDataset`, `TimeToValueDaysAsOf` |

### B4. User activation (14-day)

| Field | Specification |
|-------|----------------|
| **Status** | **PROPOSED** |
| **Business purpose** | User reached first meaningful action after user create |
| **Blocker** | No FR equivalent to FR10; user create vs account create misaligned; official metrics are account-based |

### B5. Onboarding funnel (multi-step)

| Field | Specification |
|-------|----------------|
| **Status** | **IMPLEMENTABLE_WITH_CAVEATS** |
| **Candidate steps** | Account create (dim) → `invite_user` → `login` → `view_dashboard` → `create_deal` → `move_deal_stage` |
| **Grain** | Account or user journey |
| **Numerator/denominator** | Step-wise conversion: entities reaching step N ÷ entities reaching step N-1 (or account create) |
| **Caveats** | **First observed event is often `log_activity` or pipeline actions**, not login (data-supported). Timestamps allow ordering **within** account/user but **not** proof of intended onboarding UX |
| **Attribution** | OFFICIAL; user steps need USER_OFFICIAL |
| **Validation** | Step counts monotonic non-increasing; document synthetic bias |

### B6. Deal-workflow activation

| Field | Specification |
|-------|----------------|
| **Status** | **PARTIAL** (contributes to FR10 via deal create + pipeline events) |
| **Note** | `create_deal`, `move_deal_stage`, `log_activity` measure workflow, not standalone activation KPI |

---

## C. Retention metrics

### C1. Account cohort retention (calendar D7 / D14)

| Field | Specification |
|-------|----------------|
| **Status** | **IMPLEMENTABLE_WITH_CAVEATS** |
| **Cohort anchor** | `gold_dim_accounts.CreatedDate` (or month) |
| **Qualifying activity** | Any SOURCE_VERIFIED event on `AccountId` (variant: exclude login) |
| **Retained on Dn** | ≥1 qualifying event on `CreatedDate + n days` (calendar) or within [+1, +n] rolling — **pick one standard** |
| **Maturity** | Cohort eligible only if `CreatedDate + n <= ReportAsOfDate` (use `gold_fact_activation_as_of` eligibility patterns) |
| **Limitations** | **n=120** accounts; **104** future at default as-of; exact-day probe shows low D0/D7/D14 hit rates — definition-sensitive |
| **Validation** | Eligible cohort size reported; incomplete cohorts excluded, not scored as 0% retention |

### C2. User cohort retention

Same structure with `gold_dim_users.created_date` and USER_OFFICIAL. **Status:** **IMPLEMENTABLE_WITH_CAVEATS** (weak user–account edge cases).

### C3. Rolling weekly / monthly retention

Repeat engagement in week W after signup week. **Status:** **IMPLEMENTABLE_WITH_CAVEATS**. Requires shared calendar spine (`dim_date` / `data/dim_date.txt`).

### C4. Repeat usage (feature-level)

Users/accounts with ≥2 distinct days with feature events in 28 days. **Status:** **IMPLEMENTABLE**.

---

## D. Feature adoption and usage

### D1. Feature adoption — users (ever active)

| Field | Specification |
|-------|----------------|
| **Status** | **IMPLEMENTABLE** (not materialized in Gold) |
| **Grain** | Feature × time window |
| **Numerator** | `COUNT(DISTINCT UserId)` with ≥1 event where `FeatureName = X` |
| **Denominator** | Active users in window or all users with `created_date <= as_of` |
| **Sources** | `gold_fact_product_events` |
| **Reference distribution** | dashboard, pipeline, automation, deal ~15k verified events each |

### D2. Feature adoption — accounts (ever active)

Numerator: `COUNT(DISTINCT AccountId)` OFFICIAL. **Status:** **IMPLEMENTABLE**.

### D3. Feature penetration rate

Adopted accounts ÷ eligible accounts (non-future at as-of). **Status:** **IMPLEMENTABLE_WITH_CAVEATS** (eligible denominator policy).

### D4. First feature use / time-to-first-feature

Per user or account: `MIN(EventDate)` WHERE `FeatureName = X`. **Status:** **IMPLEMENTABLE**.

### D5. Feature usage volume

`SUM(EventCount)` from aggregated fact or `COUNT(*)` detail. **Status:** **PARTIAL** — volume in Gold agg; not distinct adoption.

### D6. Feature breadth

Count of distinct `FeatureName` per account in window. **Status:** **IMPLEMENTABLE** — supports “broad vs narrow” product questions.

### D7. Feature adoption by segment

Join `gold_dim_accounts.Segment`. **Status:** **IMPLEMENTABLE** (SMB 83, MID-MARKET 37).

---

## E. Funnel and conversion

### E1. Ordered event conversion (account grain)

| Field | Specification |
|-------|----------------|
| **Status** | **IMPLEMENTABLE_WITH_CAVEATS** |
| **Definition** | Sequenced steps by `EventTimestamp` within account; conversion between steps |
| **Stitching** | `AccountId` OFFICIAL; user funnels use `UserId` |
| **Limitations** | Parallel threads, missing user on 1.9% verified rows, synthetic generation order |

### E2. Pipeline stage conversion

Events with `PipelineId` + `StageId` (24,156 rows). **Status:** **IMPLEMENTABLE** for stage transition counts; **PROPOSED** for true pipeline funnel without stage dimension table.

---

## F. Segmentation dimensions

| Dimension | Source | Status | Notes |
|-----------|--------|--------|-------|
| Segment | `gold_dim_accounts.Segment` | **IMPLEMENTABLE** | SMB / MID-MARKET |
| Account age / tenure | `AccountAgeDays`, buckets | **IMPLEMENTED** (WS-7) | Future flag |
| User tenure / recency | `gold_dim_users` | **IMPLEMENTED** | |
| Feature usage tier | Derived from events | **IMPLEMENTABLE** | |
| Geography | `gold_dim_geography` | **PARTIAL** | Derived-fixture only; **7** countries |
| Employee band / industry | Account dim | **IMPLEMENTABLE** | Inspect cardinality before publishing |
| Deal attributes | `gold_fact_deals` | **IMPLEMENTABLE** | Duplicate deal_ids — no silent dedupe |

---

## G. Product intelligence metrics (case study)

| Metric / question | Status | Label |
|-------------------|--------|-------|
| Top features by adoption | IMPLEMENTABLE | Data-supported finding |
| Returning users (WAU/MAU > DAU trend) | IMPLEMENTABLE | Data-supported |
| Activation risk (eligible but not activated) | IMPLEMENTABLE | Product recommendation input |
| Early feature mix vs later engagement correlation | IMPLEMENTABLE_WITH_CAVEATS | **Analytical hypothesis** — not causality |
| Onboarding drop-off narrative | IMPLEMENTABLE_WITH_CAVEATS | **Product recommendation** with synthetic caveat |

---

## P0 — Essential (WS-12 suggestion)

| Metric | Business value | Data readiness | Complexity | Dependencies | Risks |
|--------|----------------|----------------|------------|--------------|-------|
| User DAU/WAU/MAU | Core engagement story | High | Medium | Detail fact SQL or Gold summary | UserId nulls; activity definition |
| Account DAU/WAU/MAU | B2B buyer engagement | High | Medium | Same | Small n=120 |
| Feature adoption (distinct) | Feature strategy | High | Low–medium | Detail fact | Attribution policy |
| Feature breadth per account | Expansion narrative | High | Medium | Detail fact | |
| **Suggested WS** | **WS-12** | | | `gold_fact_product_events` | |

## P1 — Important

| Metric | Notes | Suggested WS |
|--------|-------|--------------|
| D7/D14 retention (account) | Maturity + eligibility rules | WS-13 |
| Funnel conversion (documented non-causal) | Step definitions in spec B5 | WS-13 |
| Segment engagement dashboards | Join dims | WS-13 |
| Activity recency / at-risk flags | Combine events + dim recency | WS-13 |

## P2 — Advanced

| Metric | Notes |
|--------|-------|
| User-level activation parity | New definition + governance |
| Source geography performance | Requires Excel restoration |
| Sessionization / dwell time | Not in event schema |
| Experimentation / holdouts | No experiment keys |

---

## Validation requirements (when implemented)

Each new metric should add:

1. Pytest or pipeline DQ row with documented reference snapshot bounds where stable.
2. Grain uniqueness check (no double-count from joins).
3. Attribution policy test (OFFICIAL vs SENSITIVITY).
4. As-of filter test (`EventDate <= ReportAsOfDate`).
5. Documentation cross-link to this spec and `metric_contracts.md`.

---

## Document control

| Version | Workstream | Change |
|---------|------------|--------|
| 1.0 | WS-11 | Initial audit specification; no warehouse changes |
