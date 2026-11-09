# Product workflow funnel (WS-13)

## Feasibility

Event-first-order on this synthetic dataset is **dominated by pipeline/activity events**, not login-led onboarding (see WS-11 audit). A funnel is implemented as a **descriptive, non-causal** account workflow view only.

## Implementation

**Table:** `gold_fact_account_workflow_funnel`

| Stage order | `EventNameNormalized` |
|------------:|-----------------------|
| 1 | login |
| 2 | view_dashboard |
| 3 | create_deal |
| 4 | move_deal_stage |
| 5 | log_activity |

- **Grain:** Account, OFFICIAL attribution, chronology-valid events only.
- **Reach:** Account has ≥1 qualifying event of that type (first occurrence tracked in staging SQL).
- **Eligible population (AS_OF):** Accounts with `CreatedDate <= ReportAsOfDate` (**16**).
- **Conversion:** `EntitiesReachedStage / EligibleAccounts` — **not** sequential step conversion (stages are not enforced journeys).
- **Label:** `DESCRIPTIVE_NON_CAUSAL`

Do not interpret stage reach rates as onboarding causality or friction.

## Limitations

- No enforced temporal ordering between stages in conversion math.
- User-level funnel not implemented (mixed grain avoided).
- Pre-creation events excluded via qualified event layer.
