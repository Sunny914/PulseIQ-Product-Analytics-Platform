# Product roadmap — decision intelligence slice (WS-14)

Synthetic PulseIQ CRM · priorities traceable to [`product_opportunity_backlog.md`](product_opportunity_backlog.md).

---

## Now (P0)

**Activation milestone guide (OPP-01)**

| | |
|-|-|
| Problem | Feature usage without FR10 activation on mature as-of cohort |
| User benefit | Clear path to “activated” status in first 14 days |
| Dependencies | Read existing Gold events; PM/design; no FR10 SQL change |
| Success | `IsActivatedAsOf / IsEligibleAsOf` (per cohort month) |
| Measurement limits | Current as-of **n=15** — trend usable only as simulation grows or in production |

---

## Next (P1)

1. **Rolling retention analytics (OPP-02 Phase A)** — define and implement rolling D7/D14; baseline before nudges.  
2. **Dashboard contextual entry points (OPP-03)** — if dashboard–deal gap persists at larger **n**.

| | |
|-|-|
| Dependencies | WS engineering for new metric; design for dashboard links |
| Success | Rolling user return; dashboard adoption among deal-active accounts |
| Limits | Exact-day retention remains poor proxy until rolling ships |

---

## Later (P2)

- **Segment-specific onboarding (OPP-04)** — when eligible **n** per segment supports comparison (MID-MARKET currently **2** as-of).  
- **Geography / firmographic plays** — when source geography restored.  
- **Causal experiments platform** — assignment + exposure logging (not in synthetic data today).

---

## Measurement approach

| Horizon | Tooling |
|---------|---------|
| Now | `gold_fact_activation_as_of`, qualified events, funnel reach |
| Next | New retention semantics + optional Power BI layer |
| Later | Experimentation events + production scale |

Always label **FULL_DATASET** vs **AS_OF 2026-07-11** in reviews.
