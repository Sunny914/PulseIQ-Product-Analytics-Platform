# Product opportunity backlog (WS-14)

Synthetic CRM · evidence classes: **DSF** = DATA-SUPPORTED FINDING, **OP** = OBSERVED PATTERN, **PH** = PRODUCT HYPOTHESIS, **PR** = PRODUCT RECOMMENDATION, **PE** = PROPOSED EXPERIMENT, **NM** = NOT MEASURABLE WITH CURRENT DATA  

Priority: **P0** highest · **P1** follow-up · **P2** explore later

---

## OPP-01 — First-14-day activation path (P0)

| Field | Content |
|-------|---------|
| Problem | New accounts show qualified feature/deal usage in the as-of slice but **0 / 15** meet FR10 activation. |
| Evidence | DSF: AS_OF adoption deal/automation **15/15** accounts; activation_as_of **0/15** eligible. Full-dataset **21/120** shows activation is achievable in simulation over full timeline. |
| Segment | All new accounts; AS_OF mature cohort **n=15** |
| Improvement | PR: In-product checklist + guided deal-creation milestone in days 0–14 aligned to FR10 signals (not redefining FR10). |
| Expected behaviour | More eligible accounts meeting existing activation criteria without changing formulas. |
| Success metrics | `IsActivatedAsOf` rate among `IsEligibleAsOf`; days-to-first-`create_deal` (qualified). |
| Guardrails | Qualified engagement DAU; quarantine rate unchanged. |
| Effort | Medium (UX + copy; no new event types required) |
| Confidence | Medium — tension is data-real; solution is hypothetical |
| Risks | Tiny sample may not validate quickly; FR10 may be intentionally strict |

---

## OPP-02 — Return-visit measurement and nudges (P1)

| Field | Content |
|-------|---------|
| Problem | Exact-day account D7/D14 retention **0%**; users **<4%** D7. Unclear if users return on nearby days. |
| Evidence | DSF: `gold_fact_retention_cohort` AS_OF rates above. PH: calendar exact-day metric is harsh. |
| Segment | Users first; accounts when **n** grows |
| Improvement | PR: Add rolling 7-day return metric to analytics; evaluate gentle return prompts after inactivity. |
| Success metrics | Rolling 7-day user return rate (new Gold or semantic layer — **instrumentation needed**). |
| Guardrails | Login-only inflation; notification fatigue |
| Effort | Analytics Medium + product Medium |
| Confidence | Low–medium on intervention; high on measurement gap |
| Risks | NM for rolling metric today without WS engineering |

---

## OPP-03 — Dashboard engagement depth (P1)

| Field | Content |
|-------|---------|
| Problem | Dashboard feature reach **14/15** vs deal **15/15**; funnel `view_dashboard` reach **75%**. |
| Evidence | OP: adoption + funnel tables AS_OF. |
| Segment | Accounts with deal usage but no/low dashboard ( **≤1** in as-of slice) |
| Improvement | PR: Contextual dashboards linked from deal/pipeline screens. |
| Success metrics | Qualified `view_dashboard` events per active account; dashboard feature adoption count. |
| Guardrails | Deal workflow completion time (if instrumented later) |
| Effort | Medium |
| Confidence | Low — small gap, small **n** |

---

## OPP-04 — Segment-specific onboarding (P2)

| Field | Content |
|-------|---------|
| Problem | MID-MARKET vs SMB differences unclear. |
| Evidence | NM: AS_OF MID-MARKET **2** eligible, **1** active. OP: breadth similar (4.0 vs 3.86). |
| Improvement | Defer dedicated tracks. |
| Priority | P2 |

---

## Prioritisation summary

| ID | Priority | Value | Evidence | Confidence | Effort |
|----|----------|-------|----------|------------|--------|
| OPP-01 | P0 | High | Strong DSF | Medium | Medium |
| OPP-02 | P1 | Medium | DSF + PH | Low–Med | Medium |
| OPP-03 | P1 | Medium | OP | Low | Medium |
| OPP-04 | P2 | Low | NM | Low | High |
