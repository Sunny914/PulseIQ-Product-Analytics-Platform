# Product requirements proposals (WS-14)

Proposals for the **two highest-priority** opportunities (OPP-01, OPP-02). **Proposed only** — no shipped features, no experiment results.

---

## Proposal 1 — OPP-01: Activation milestone guide (P0)

### Problem
Eligible mature accounts (as-of **n=15**) show CRM feature usage but **0%** FR10 as-of activation (**0 / 15**).

### Evidence (DSF)
- `gold_fact_feature_adoption_account` AS_OF: deal/automation adopters **15**.
- `gold_fact_activation_as_of`: `IsEligibleAsOf` **15**, `IsActivatedAsOf` **0**.
- Funnel reach: `create_deal` **15/16** eligible — usage exists; activation rule bundle not satisfied.

### Hypothesis (PH)
A guided **14-day checklist** mapping to existing events (deal create + qualifying core interaction) will increase **eligible** activation without changing FR10 definitions.

### Proposed solution
Account-admin onboarding panel: Day 0–14 tasks — invite user, create deal, log activity, enable automation — each tied to existing `EventNameNormalized` values. Progress from warehouse fields only (no new events v1).

### Target users
Account admins on accounts with `CreatedDate` within 14 days of today/`ReportAsOfDate`.

### User stories
1. As an **account admin**, I see which activation milestones remain in my first 14 days so I know what to do next.
2. As a **CS lead**, I see which eligible accounts completed milestones before window end.

### Acceptance criteria
1. Checklist displays only milestones definable from current Gold events.
2. Completion states derived from `gold_fact_qualified_product_events` rules (chronology-valid).
3. Does not alter `gold_fact_advanced_activation` SQL.

### Success metrics
- Primary: `COUNT(IsActivatedAsOf) / COUNT(IsEligibleAsOf)` per monthly cohort.
- Secondary: Median days to first qualified `create_deal` post-`CreatedDate`.

### Guardrails
- Qualified user DAU (no collapse).
- QUARANTINED attribution share stable.

### Experiment proposal (PE)
| Element | Design |
|---------|--------|
| Hypothesis | Checklist increases eligible as-of activation rate |
| Treatment | Checklist + email nudges |
| Control | Status quo onboarding |
| Unit | Account (randomize new signups) |
| Primary metric | FR10 `IsActivatedAsOf` at day 14 |
| Guardrails | Support volume (not in data); login rate |
| Duration | ≥8 weeks for **n≥30** eligible — **NOT MEASURABLE** at current synthetic scale |

### Instrumentation gaps
Cohort assignment flag; optional checklist impression/click events (not in current schema).

---

## Proposal 2 — OPP-02: Rolling return measurement (P1)

### Problem
Exact-day D7 account retention **0%** limits product judgement on repeat use.

### Evidence (DSF)
- `gold_fact_retention_cohort` AS_OF: account D7 **0/15**, user D7 **2/56**.

### Hypothesis (PH)
**Rolling 7-day return** (activity on any day in [D1–D7]) will show higher return than exact-day D7 and better inform nudges.

### Proposed solution
**Phase A (analytics):** Document + optional future Gold metric for rolling return; no user-facing change until baseline exists.  
**Phase B (product):** Inactivity nudge after 7 days without qualified events (if rolling return < benchmark).

### Target users
Active users with `IsOfficialUserQualified` history.

### User stories
1. As a **PM**, I view rolling 7-day user return by signup cohort to judge onboarding quality.
2. As a **user**, I receive a helpful prompt when I have not used core CRM features in a week (Phase B).

### Acceptance criteria (Phase A)
1. Metric definition in `product_analytics_metric_specification.md`.
2. Reconciles to detail fact distinct users; chronology-valid only.

### Success metrics
- Primary (Phase A): Rolling D7 user return rate among mature cohorts.
- Primary (Phase B): Δ rolling D7 vs control (experiment).

### Guardrails
- Distinct-user login spam; account-level FR10 activation.

### Experiment proposal (PE)
| Element | Design |
|---------|--------|
| Hypothesis | Nudge increases rolling D7 user return |
| Treatment | Email + in-app reminder |
| Control | No nudge |
| Unit | User |
| Primary | Rolling D7 return (qualified events) |
| Duration | 4 weeks; needs larger live population — **synthetic n too small** |

### Instrumentation gaps
Rolling retention not in current Gold; notification send/dismiss events absent.
