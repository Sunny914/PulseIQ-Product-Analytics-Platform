# Retention and cohort analysis (WS-13)

See [`chronology_integrity_audit.md`](chronology_integrity_audit.md) for the WS-13 gate.

## Implemented models

**Table:** `gold_fact_retention_cohort`

| Field | Definition |
|-------|------------|
| **Cohort anchor** | `CreatedDate` on `gold_dim_accounts` / `gold_dim_users` |
| **Retention windows** | **D7**, **D14** — **exact calendar day** (`CohortAnchorDate + n days`) |
| **Qualifying activity** | Any `IsOfficialAccountQualified` / `IsOfficialUserQualified` event on that exact day |
| **Denominator** | Entities where `CohortAnchorDate + n <= ReportAsOfDate` (AS_OF) or all cohorts (FULL_DATASET) |
| **Numerator** | Eligible entities with qualifying activity on the exact retention day |
| **Interpretation** | `EXACT_CALENDAR_DAY` — not a rolling 7-day return window |
| **Contexts** | `FULL_DATASET`, `AS_OF` |
| **Attribution** | OFFICIAL only |

Immature cohorts are excluded from denominators, not scored as zero retention.

## Tests

`tests/test_ws13_chronology_retention.py`

## Known limitations

- Small eligible AS_OF cohort (16 accounts / subset of users).
- Synthetic pre-creation noise removed from analytics, not from source.
- Rolling weekly retention not materialized (P1).
