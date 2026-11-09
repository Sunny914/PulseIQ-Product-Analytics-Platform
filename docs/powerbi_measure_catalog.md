# Power BI measure catalog (WS-15)

**Rules:** Filter `ReportContext` before comparing KPIs. Do not sum `ActiveEntityCount` across periods without `PeriodType`. Prefer **Gold values** over re-derived DAX logic. Synthetic data only.

## Reporting context

```dax
Report Context Selected = SELECTEDVALUE ( fact_engagement_periodic[ReportContext], "AS_OF" )

Report As Of Date =
VAR d = SELECTEDVALUE ( fact_engagement_periodic[ReportAsOfDate] )
RETURN IF ( ISBLANK ( d ), DATE ( 2026, 7, 11 ), d )

Synthetic Disclaimer =
"Synthetic CRM data — illustrative portfolio analytics, not production KPIs."
```

## Engagement (from `fact_engagement_periodic`)

Grain: one row per `ReportContext`, `PeriodType`, `PeriodStartDate`, `EntityType` (USER | ACCOUNT), `AttributionPopulation`.

```dax
// Filter visuals: ReportContext, PeriodType = "DAY" | "WEEK" | "MONTH", EntityType

User DAU =
CALCULATE (
    SUM ( fact_engagement_periodic[ActiveEntityCount] ),
    fact_engagement_periodic[EntityType] = "USER",
    fact_engagement_periodic[PeriodType] = "DAY",
    fact_engagement_periodic[AttributionPopulation] = "OFFICIAL"
)

User WAU =
CALCULATE (
    SUM ( fact_engagement_periodic[ActiveEntityCount] ),
    fact_engagement_periodic[EntityType] = "USER",
    fact_engagement_periodic[PeriodType] = "WEEK",
    fact_engagement_periodic[AttributionPopulation] = "OFFICIAL"
)

User MAU =
CALCULATE (
    SUM ( fact_engagement_periodic[ActiveEntityCount] ),
    fact_engagement_periodic[EntityType] = "USER",
    fact_engagement_periodic[PeriodType] = "MONTH",
    fact_engagement_periodic[AttributionPopulation] = "OFFICIAL"
)

Account DAU =
CALCULATE (
    SUM ( fact_engagement_periodic[ActiveEntityCount] ),
    fact_engagement_periodic[EntityType] = "ACCOUNT",
    fact_engagement_periodic[PeriodType] = "DAY",
    fact_engagement_periodic[AttributionPopulation] = "OFFICIAL"
)

Account WAU = /* same pattern, EntityType = ACCOUNT, PeriodType = WEEK */

Account MAU = /* same pattern, EntityType = ACCOUNT, PeriodType = MONTH */
```

**Note:** For trend lines, use `PeriodStartDate` on axis — do not aggregate multiple contexts on one card.

## Feature adoption (account / user facts)

Tables: `fact_feature_adoption_account`, `fact_feature_adoption_user`. Filter `ReportContext`, `AttributionPopulation = OFFICIAL`.

```dax
Distinct Account Adopters =
SUMX (
    VALUES ( fact_feature_adoption_account[AccountId] ),
    IF ( fact_feature_adoption_account[IsAdopter] = TRUE (), 1, 0 )
)
// Simpler when table is one row per account-feature:
Distinct Account Adopters =
CALCULATE (
    DISTINCTCOUNT ( fact_feature_adoption_account[AccountId] ),
    fact_feature_adoption_account[IsAdopter] = TRUE ()
)

Feature Adoption % (Accounts) =
DIVIDE (
    CALCULATE (
        DISTINCTCOUNT ( fact_feature_adoption_account[AccountId] ),
        fact_feature_adoption_account[IsAdopter] = TRUE ()
    ),
    CALCULATE (
        DISTINCTCOUNT ( dim_accounts[AccountId] ),
        dim_accounts[IsFutureCreated] = FALSE ()  // context-dependent; prefer Gold denominator column if present
    )
)

Repeat Usage (qualified events) =
SUM ( fact_feature_adoption_account[QualifiedFeatureEventCount] )

Feature Breadth (accounts) =
AVERAGE ( fact_feature_breadth_account[DistinctFeaturesAdopted] )
```

Document denominator per visual: as-of eligible population is **≤15** accounts.

## Retention (`fact_retention_cohort`)

Exact-day return only — **not rolling retention**.

```dax
D7 Eligible Entities =
CALCULATE (
    SUM ( fact_retention_cohort[EligibleEntities] ),
    fact_retention_cohort[RetentionWindow] = "D7",
    fact_retention_cohort[AttributionPopulation] = "OFFICIAL"
)

D7 Retained Entities =
CALCULATE (
    SUM ( fact_retention_cohort[RetainedEntities] ),
    fact_retention_cohort[RetentionWindow] = "D7"
)

D7 Retention Rate =
CALCULATE (
    MAX ( fact_retention_cohort[RetentionRate] ),
    fact_retention_cohort[RetentionWindow] = "D7"
)
// Prefer Gold RetentionRate — do not recompute from immature cohorts.

D14 Eligible Entities = /* RetentionWindow = "D14" */
D14 Retained Entities = /* RetentionWindow = "D14" */
D14 Retention Rate = /* RetentionWindow = "D14" */

Retention Definition Note =
"Exact calendar-day return (D7/D14); not rolling 7-day retention."
```

Filter `EntityType` (USER vs ACCOUNT) on separate visuals.

## Activation (separate from engagement)

**Full dataset:** `fact_advanced_activation`  
**As-of:** `fact_activation_as_of`

```dax
FR10 Activated Accounts (full dataset) =
CALCULATE (
    DISTINCTCOUNT ( fact_advanced_activation[AccountId] ),
    fact_advanced_activation[IsActivated] = TRUE ()
)

Eligible Accounts (full dataset) = 120  // or COUNTROWS dim where appropriate

Full Dataset Activation Rate =
DIVIDE ( [FR10 Activated Accounts (full dataset)], 120 )  // 21/120 = 17.5%

Full Dataset Mean TTV (days) =
AVERAGE (
    FILTER (
        fact_advanced_activation,
        fact_advanced_activation[IsActivated] = TRUE ()
    ),
    fact_advanced_activation[TimeToValueDays]
)  // ~9.904762

As Of Eligible Accounts =
CALCULATE (
    COUNTROWS ( fact_activation_as_of ),
    fact_activation_as_of[IsEligibleAsOf] = TRUE ()
)  // 15

As Of Activated Accounts =
CALCULATE (
    COUNTROWS ( fact_activation_as_of ),
    fact_activation_as_of[IsEligibleAsOf] = TRUE (),
    fact_activation_as_of[IsActivatedAsOf] = TRUE ()
)  // 0

As Of Activation Rate =
DIVIDE ( [As Of Activated Accounts], [As Of Eligible Accounts] )  // 0%

Activation vs Engagement Note =
"FR10 activation (deal + core signals in 14 days) is separate from qualified product engagement."
```

## Segmentation

`fact_segment_product_metrics` — show `EligibleAccounts` on every card.

```dax
Segment Account Count = SUM ( fact_segment_product_metrics[EligibleAccounts] )

Segment Active Accounts = SUM ( fact_segment_product_metrics[ActiveAccounts] )

As Of Sample Warning =
"As of 2026-07-11: 16 accounts created; 15 window-complete for retention/activation."
```

## Funnel (`fact_account_workflow_funnel`)

```dax
Funnel Stage Reach % = MAX ( fact_account_workflow_funnel[ReachRate] )

Funnel Disclaimer =
"Descriptive event reach; not a sequential conversion funnel."
```
