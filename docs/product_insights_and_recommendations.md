# PulseIQ — Product insights and recommendations (WS-14)

> **Synthetic disclosure:** PulseIQ is a **fictional B2B SaaS CRM** with a **synthetic** dataset. Findings describe patterns **inside the simulation**, not real customers, revenue, or production performance. No customer interviews, experiments, or causal claims are implied.

**Evidence base:** Chronology-qualified Gold analytics (`ReportAsOfDate = 2026-07-11`, `FULL_DATASET` where noted), FR10 activation facts, disposable DB `artifacts/ws13_final.duckdb` (read-only extraction, Nov 2026).

**Populations:** Official conclusions use **SOURCE_VERIFIED** + qualified events (`IsOfficialAccountQualified` / `IsOfficialUserQualified`). Sensitivity populations cited only where noted.

---

## Executive summary

Among the **16** accounts that existed by July 11, 2026, product **engagement and feature adoption appear healthy** under chronology-valid rules: **15** accounts adopted at least one feature, **14** show **broad** (3+) feature use, and funnel **stage reach** on deal/pipeline actions is high.

By contrast, **FR10 account activation** among the **15** window-complete eligible accounts is **0% as-of** (unchanged canonical metric: **0 / 15**), while **full-dataset** activation remains **21 / 120 (17.5%)**. That split suggests that **workflow-based activation (deal + core event in 14 days)** is a stricter bar than **general CRM feature usage**, and that the small mature-as-of cohort does not yet meet FR10 — not that the product has zero usage.

**DATA-SUPPORTED FINDING:** Exact-day account D7/D14 retention is **0%** on the as-of mature cohort (0 / 15 on day 7 and day 14). User retention is low but non-zero (D7 **3.6%**, D14 **1.9%** on larger eligible user denominators). **PRODUCT HYPOTHESIS:** Day-exact retention may understate return behaviour; rolling-window measurement is needed before prioritising churn-style interventions.

**PRODUCT RECOMMENDATION (P0):** Clarify and support the **first-14-day activation path** (deal creation + qualifying core usage) for new accounts — the gap between high feature reach and **0% as-of eligible activation** is the strongest actionable tension in the as-of slice.

---

## Product context

**Assumption (labeled):** The product is a multi-tenant CRM for sales teams with dashboard analytics, deal pipelines, activity logging, and automation.

| Dimension | From project data |
|-----------|-------------------|
| Accounts | 120 synthetic tenants; SMB **83**, MID-MARKET **37** (full dim) |
| Users | 400 |
| Core features (JSON) | dashboard, automation, pipeline, deal |
| Canonical events | login, view_dashboard, create_deal, move_deal_stage, log_activity, invite_user, enable_automation |

**Successful adoption (assumption):** Accounts combine pipeline/deal work with repeat team usage; **FR10 activation** additionally requires provable deal workflow + core product signals within 14 days of signup.

---

## Problem statement

A product team needs consistent answers to: *Are new accounts reaching meaningful value? Which features drive usage? Do users return? Do segments differ?*  

Without **chronology-safe** metrics and explicit **full-dataset vs as-of** labelling, synthetic timestamp noise can falsely imply universal adoption. WS-13 corrected that; WS-14 interprets the **trustworthy** layer for decisions.

---

## Analytical evidence (AS_OF unless noted)

### A. Engagement — **OBSERVED PATTERN**

| Metric | Evidence | Class |
|--------|----------|--------|
| User MAU (official) | Jun **11**, May **14**, Jul partial **10** users | OBSERVED PATTERN |
| Account MAU | Jun **12**, May **9**, Jul **7** | OBSERVED PATTERN |
| User DAU range | Max **3**, min **1** per day | OBSERVED PATTERN |
| Sample | Only users/accounts **created ≤ 2026-07-11** | DATA-SUPPORTED FINDING |

User activity exceeds account activity in some months — **DATA-SUPPORTED FINDING** (multi-user accounts). **Not causal.**

### B. Feature adoption — **DATA-SUPPORTED FINDING**

AS_OF official account adopters by feature (distinct accounts, **n ≤ 15**):

| Feature | Adopters |
|---------|--------:|
| deal | 15 |
| automation | 15 |
| pipeline | 14 |
| dashboard | 14 |

**FULL_DATASET:** **118** distinct adopting accounts (chronology-qualified) vs **15** as-of — illustrates reporting-context separation.

Breadth AS_OF: **14** `broad_3plus_features`, **1** `moderate_2_features`.

### C. Retention — **DATA-SUPPORTED FINDING**

| Entity | Window | Eligible | Retained | Rate |
|--------|--------|---------:|---------:|-----:|
| Account | D7 | 15 | 0 | 0.0 |
| Account | D14 | 15 | 0 | 0.0 |
| User | D7 | 56 | 2 | 0.036 |
| User | D14 | 53 | 1 | 0.019 |

**Interpretation:** Exact calendar-day return is rare in the simulation for accounts. User denominators are larger but rates remain low. **NOT MEASURABLE WITH CURRENT DATA** for robust segment retention cuts (MID-MARKET **n = 2** eligible).

### D. Activation and TTV — **DATA-SUPPORTED FINDING**

| Metric | Value | Context |
|--------|------:|---------|
| Full-dataset activated | **21 / 120** (17.5%) | FR10; entire timeline |
| Mean TTV (activated) | **~9.905 days** | Full-dataset |
| As-of eligible | **15** | Window complete by 2026-07-11 |
| As-of eligible activated | **0 / 15** | FR10 + eligibility rules |
| Future-created accounts | **104** | Excluded from as-of engagement denominators |

**Engagement ≠ activation:** High deal/pipeline adoption coexists with **0%** as-of eligible activation — definitions differ (deal-in-window + core event vs any qualified event).

### E. Funnel — **OBSERVED PATTERN**

Descriptive **stage reach** (eligible **16** accounts), not conversion:

| Stage | Reach | Rate |
|-------|------:|-----:|
| create_deal | 15 | 93.8% |
| move_deal_stage | 15 | 93.8% |
| login | 13 | 81.3% |
| log_activity | 13 | 81.3% |
| view_dashboard | 12 | 75.0% |

**Cannot** claim onboarding drop-off order; first events in WS-11 were often pipeline/activity, not login.

### F. Segmentation — **OBSERVED PATTERN** (small n)

AS_OF `gold_fact_segment_product_metrics`:

| Segment | Eligible | Active | Activated (FR10) | Avg breadth |
|---------|--------:|-------:|------------------:|------------:|
| SMB | 14 | 14 | 0 | 3.86 |
| MID-MARKET | 2 | 1 | 0 | 4.0 |

**PRODUCT HYPOTHESIS:** SMB shows fuller active coverage within the tiny as-of slice; MID-MARKET sample **not** sufficient for segment bets.

### Recency (accounts, AS_OF)

| Bucket | Count |
|--------|------:|
| active_0_6_days | 5 |
| active_7_29_days | 8 |
| active_30_89_days | 2 |

---

## Major findings (summary)

1. **As-of cohort is tiny (16 accounts, 15 activation-eligible)** — all segment and retention conclusions are exploratory.
2. **Feature usage is wide** among mature accounts; **FR10 activation is none** on that slice.
3. **Account exact-day retention is zero** in qualified analytics; user retention is low.
4. **Funnel reach is high on deal actions**, lower on dashboard — descriptive only.
5. **104 future accounts** drive full-dataset activation share; never blend with as-of KPIs.

---

## Product opportunities

See [`product_opportunity_backlog.md`](product_opportunity_backlog.md) for prioritised detail. Top themes:

1. **Activation path clarity (P0)** — engagement without eligible activation.
2. **Measurement of return behaviour (P1)** — exact-day retention vs product reality.
3. **Dashboard value proposition (P1)** — slightly lower reach than deal features.

---

## Limitations

- Synthetic data; pre-creation events remain in source but excluded from official analytics.
- No experiments, revenue, churn labels, or qualitative research.
- Causal language prohibited.
- Geography is derived-fixture in pipeline clones.

---

## Recommendations

1. Treat **as-of KPIs** as the executive “state on July 11, 2026” layer; treat **full-dataset** as simulation-wide benchmarking only.
2. Prioritize **activation onboarding** over generic feature nudges for new accounts (P0).
3. Add **rolling retention** and **funnel sequencing** analytics before roadmap bets on retention mechanics (P1).
4. Defer **segment-specific plays** until real samples exist or synthetic cohorts mature.

Detail: [`product_requirements_proposals.md`](product_requirements_proposals.md), [`product_roadmap.md`](product_roadmap.md).
