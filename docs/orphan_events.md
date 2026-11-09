# Orphan product events — account attribution and quarantine (WS-5 / WS-5.2)

## Problem

Non-test product events (`is_test_event = FALSE`) include **641** rows with a NULL source `account_id` while still carrying `user_id` and/or `deal_id`. Account-level metrics that join only on source `account_id` under-count or drop these events.

Silver excludes **1,195** test events from raw (**61,747 → 60,552**). Among raw null accounts, **12** are test events → **641** orphan **event records** in Silver (not “641 distinct non-null source EventIds”; use **`event_sk`** as the internal grain).

## Reconciled counts (snapshot-backed temp DB)

| Metric | Count |
|--------|------:|
| Silver product events | 60,552 |
| SOURCE_VERIFIED (valid source account) | 59,911 |
| ENRICHED (orphan, single unambiguous signal) | 226 |
| QUARANTINED (orphan conflict / unresolved + invalid source) | 415 |
| Invalid non-null source account | 0 |

Orphan signal buckets (WS-5.1, mutually exclusive):

| Bucket | Count | WS-5.2 outcome |
|--------|------:|----------------|
| USER_ONLY | 216 | ENRICHED (`USER_DIM`, `USER_ACCOUNT_ONLY`) |
| DEAL_ONLY | 10 | ENRICHED (`DEAL_RAW`, `DEAL_ACCOUNT_ONLY`) |
| CONFLICTING | 406 | QUARANTINED |
| UNRESOLVED | 9 | QUARANTINED |
| CONSISTENT (user = deal) | 0 | ENRICHED (`USER_DEAL_CONSISTENT`) if present |

**226** policy-safe enrichments = 216 + 10. **415** quarantined = 406 + 9.

## Relationship investigation

- **User path:** `silver_users.account_id` validated against `bronze_accounts` (same account grain as Gold dim).
- **Deal path:** `raw__deals` grouped by `deal_id`; attribution uses the account only when **exactly one distinct** valid `account_id` exists (duplicate deal rows with the same account are allowed; multi-account deal keys are rejected).
- **Naive join** of orphans to `raw__deals` inflates **416 → 420** rows (+4); Silver attribution does **not** join deals row-wise and keeps **60,552** event grain.

## Silver columns

| Column | Meaning |
|--------|---------|
| `account_id` | Original source account (unchanged) |
| `account_id_resolved` | Account for analytics when verified or safely enriched |
| `account_resolution_status` | `SOURCE_VERIFIED` \| `ENRICHED` \| `QUARANTINED` |
| `account_resolution_method` | `SOURCE`, `USER_DIM`, `DEAL_RAW`, `USER_DEAL_CONSISTENT`, or `NONE` |
| `account_resolution_reason` | Human-readable rule outcome |

## Rules (summary)

1. **SOURCE_VERIFIED** — non-null `account_id` exists in `bronze_accounts`.
2. **ENRICHED / USER_ONLY** — null source account; valid user account; no unambiguous deal account; no conflict.
3. **ENRICHED / DEAL_ONLY** — null source account; unambiguous valid deal account; no valid user account.
4. **ENRICHED / consistent** — user and deal accounts agree (expected **0** today).
5. **QUARANTINED / CONFLICTING** — user and deal accounts both valid but differ (**406**); never auto-pick one side.
6. **QUARANTINED / UNRESOLVED** — no valid user or deal account (**9**).
7. **QUARANTINED / invalid source** — non-null `account_id` not in dim (**0** today).

## Quarantine access

View **`silver_product_events_quarantine`**: all `QUARANTINED` rows (**415**), full Silver column set.

## Gold detail fact

- **`AccountId`** — original source account only.
- **`AccountIdResolved`**, **`AccountResolutionStatus`**, **`AccountResolutionMethod`**, **`AccountResolutionReason`** — explicit resolved attribution.
- Quarantined events remain in **`gold_fact_product_events`**.
- **`gold_fact_product_events_aggregated`** still groups on source **`AccountId`** only (unchanged in WS-5.2).

## Analytics guidance

| Use case | Filter / field |
|----------|----------------|
| Conservative / source-only | `AccountResolutionStatus = 'SOURCE_VERIFIED'` and `AccountId` |
| Include safe imputation | `AccountResolutionStatus IN ('SOURCE_VERIFIED','ENRICHED')` and `AccountIdResolved` |
| Exclude ambiguous orphans | exclude `QUARANTINED` from account rollups |
| Event grain | always `EventSk` |

## Limitations

- User attribution depends on **`silver_users`** and account dim grain; nine users have NULL/invalid account linkage.
- Deal attribution uses **raw** deals, not fan-out-prone Gold deal facts.
- **`sql/data/raw_geography.xlsx`** is missing from the repo; temp pipelines stub geography from account country codes so `silver_accounts` / Gold dim can run in tests.
- Authoritative dev DB is not updated by WS-5.2 tests; re-run Silver/Gold locally after pulling changes.

## Validation

Automated: `tests/test_orphan_quarantine.py` on temporary DuckDB built from `data/source_snapshot` Parquet files.
