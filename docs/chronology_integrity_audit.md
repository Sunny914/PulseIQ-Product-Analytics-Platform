# Event chronology integrity audit (WS-13 gate)

**Database:** disposable pipeline output (`ReportAsOfDate = 2026-07-11`). **Source data not modified.**

## Finding summary

Synthetic raw events often occur **before** entity `CreatedDate`. WS-12 AS_OF metrics also counted **events** on/before the reporting date from **future-created** accounts (104 of 120), producing impossible adoption coverage (120/120 accounts).

| Classification | Account events (SOURCE_VERIFIED) | Notes |
|----------------|----------------------------------|--------|
| **VALID** | 28,750 | `EventDate >= AccountCreatedDate` |
| **PRE_CREATION_EVENT** | 31,161 | 117 accounts |
| **UNKNOWN** (null account) | — | Orphan source rows |
| **FUTURE_ENTITY_AS_OF** | (entity flag) | 104 accounts created after 2026-07-11 |

| User events (with UserId) | Count |
|---------------------------|------:|
| **PRE_CREATION_EVENT** | 27,332 (379 users) |

**Future-created accounts with events ≤ ReportAsOfDate:** 104 (all future accounts) — historical AS_OF activity must exclude these entities from denominators and adoption.

## Correction policy (WS-13)

1. **`gold_fact_qualified_product_events`** — chronology flags; `IsOfficialAccountQualified` / `IsOfficialUserQualified` require `EventDate >= CreatedDate`.
2. **WS-12 Gold models** — reimplemented on qualified events; AS_OF adds `EntityCreatedDate <= ReportAsOfDate`.
3. **Activation (FR10)** — unchanged logic and results (21/120, 0/15, TTV ~9.904762); uses original source rules on deals/events, not WS-12 analytics tables.

## WS-12 as-of metrics — before vs after

| Metric (AS_OF, OFFICIAL) | Before WS-13 | After WS-13 |
|--------------------------|-------------:|------------:|
| Distinct accounts with feature adoption | 120 | **15** |
| Eligible accounts (created ≤ as-of) | (not enforced) | **16** |
| Account funnel eligible population | 120 | **16** |

Dashboard adoption for one mature account may be absent under chronology-valid AS_OF rules (15/16 adopters).

## Limitations

Pre-creation timestamps remain in **raw/silver/detail** facts for audit. Official product analytics reads **qualified** events only.
