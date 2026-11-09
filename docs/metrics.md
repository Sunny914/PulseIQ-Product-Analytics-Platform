# PulseIQ metrics reference (WS-8 / WS-8.1)

## Activation entity

**Account** — one row per account in `gold_dim_accounts` (120 in reference snapshots).

## Existing advanced activation (unchanged — FR10)

**Table:** `gold_fact_advanced_activation`  
**Script:** `sql/gold/gold_fact_advanced_activation.py`

An account is **activated** when **both** are true within the **first 14 days after account creation** (inclusive window):

1. ≥1 **core product event** in `gold_fact_product_events` with **`HasDealContext = TRUE`** (`deal_id IS NOT NULL` on the event), joined on **source `AccountId`**.
2. ≥1 deal in `gold_fact_deals` with **`CreatedDate`** in the same window, joined on **`AccountId`**.

**Window (inclusive):**

```sql
event_or_deal_date BETWEEN CreatedDate AND (CreatedDate + INTERVAL 14 DAY)
```

**Activation date:** `GREATEST(FirstCoreEventDate, FirstDealDate)`  
**Time to value (TTV):** `DATE_DIFF('day', CreatedDate, ActivationDate)` — only for activated accounts; NULL otherwise.

**Attribution:** Source **`AccountId` only** — enriched/quarantined orphan events are excluded (see `docs/orphan_events.md`).

### Full-dataset activation rate (metric A)

| Numerator | Denominator | Reference value |
|-----------|-------------|-----------------|
| `COUNT(*) WHERE IsActivated` | All accounts in activation fact | **21 / 120 = 17.5%** |

**Important:** **17.5% is a full-dataset, whole-cohort metric.** It is **not** the activation rate as of the default reporting date **2026-07-11**.

## Supplementary as-of activation (WS-8.1)

**Table:** `gold_fact_activation_as_of`  
**Script:** `sql/gold/gold_fact_activation_as_of.py`  
**Reporting date:** `get_as_of_date()` — default **`2026-07-11`**, override **`PULSEIQ_AS_OF_DATE`**.

One row per account. Adds cohort maturity and explicit denominators without changing the advanced activation logic.

| Column | Meaning |
|--------|---------|
| `ReportAsOfDate` | Reporting reference date |
| `ActivationWindowEndDate` | `CreatedDate + 14 days` |
| `IsFutureCreated` | `CreatedDate > ReportAsOfDate` |
| `IsWindowCompleteAsOf` | Full 14-day window ended on or before `ReportAsOfDate` |
| `IsEligibleAsOf` | `CreatedDate ≤ ReportAsOfDate` AND window complete |
| `IsActivatedFullDataset` | Same as `IsActivated` in advanced activation |
| `IsActivatedAsOf` | Eligible AND full-dataset activated |
| `TimeToValueDaysFullDataset` | Same as `TimeToValueDays` in advanced activation (NULL if not activated) |
| `TimeToValueDaysAsOf` | TTV only when `IsEligibleAsOf` AND `IsActivatedAsOf`; otherwise NULL |

### As-of eligible activation rate (metric B)

| Numerator | Denominator |
|-----------|-------------|
| `COUNT(*) WHERE IsEligibleAsOf AND IsActivatedAsOf` | `COUNT(*) WHERE IsEligibleAsOf` |

**Ineligible accounts** (future-created or immature window) are **excluded from the denominator** — they must **not** be treated as unactivated in metric B.

**Reference snapshot (ReportAsOfDate = 2026-07-11):**

| Cohort | Count |
|--------|------:|
| Accounts created by reporting date | 16 |
| Window complete (eligible) | **15** |
| Window incomplete | **1** |
| Created after reporting date | **104** |
| Eligible activated | **0** |
| **As-of activation rate** | **0 / 15 = 0%** |

## Cohort maturity and right-censoring

Accounts still inside their 14-day window at `ReportAsOfDate` are **immature** — activation is unknown, not false. Use `IsWindowCompleteAsOf` / `IsEligibleAsOf` for filtering.

## TTV distribution (full-dataset activated, n=21)

| Statistic | Days (reference) |
|-----------|-----------------:|
| Mean | ~**9.904762** |
| Median | **10** |
| Min / Max | 4 / 14 |

Do not impute TTV = 0 for unactivated or ineligible accounts.

**As-of TTV:** Use **`TimeToValueDaysAsOf`** for metric B cohorts only. Full-dataset TTV remains on **`TimeToValueDaysFullDataset`** (and on `gold_fact_advanced_activation.TimeToValueDays`).

## Segment analysis

Join `gold_fact_activation_as_of` to `gold_dim_accounts` on `AccountId`. Compute rates using **`IsEligibleAsOf`** as denominator only. Flag small samples (e.g. eligible n &lt; 20).

## Source vs enriched attribution

Official activation uses **source `AccountId`**. Counterfactual enriched joins do not change the **21** activated count on reference data (WS-8 audit).

## Synthetic dataset limitations

- Many **future-dated** accounts and events.
- **HasDealContext** is weak (non-null `deal_id` only).
- Full-dataset **21/120** mixes cohorts that did not exist on **2026-07-11**.
- Use **metric A** for FR10 regression; use **metric B** for historical as-of reporting.
