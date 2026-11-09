# PulseIQ — Event Identity (`event_sk`)

## Why `event_sk` is required

The raw product-events stream includes **625** rows with a null source `event_id` (616 after excluding test events in Silver). Gold previously exposed `EventId` as the only key, so **616 rows could not be uniquely identified** despite representing distinct events.

Analytics (funnel grain, joins, deduplicated counts) needs a **non-null, unique** key per event row while **preserving the source `event_id`** exactly as ingested (including NULL).

## `EventId` vs `event_sk`

| Field | Layer | Role |
|-------|--------|------|
| `event_id` / `EventId` | Bronze / Silver / Gold | **Source system identifier**; unchanged; may be NULL |
| `event_sk` / `EventSk` | Silver / Gold | **Internal stable surrogate**; never NULL; unique per row |
| `event_sk_type` | Silver | `SOURCE` when `event_id` present, else `SURROGATE` |

Bronze and raw snapshots are **not** modified.

## Surrogate methodology

Implemented in `sql/silver/silver_product_events.py` using fragments from `sql/event_sk_sql.py`.

### When `event_id` IS NOT NULL

```text
event_sk = 'SRC-' || event_id
```

Non-null source IDs are already unique in the dataset (verified: 0 duplicate non-null `event_id` values).

### When `event_id` IS NULL

1. Build a **canonical payload string** from immutable source fields (pipe-separated, empty string for NULLs):

   - `event_name`, `user_id`, `account_id`, `deal_id`
   - `event_timestamp`, `event_properties`, `source_system`
   - `platform`, `device_type`, `app_version`, `country_code`

2. `payload_digest = sha256(canonical_payload)` (DuckDB hex string).

3. **Duplicate payload handling:** `ROW_NUMBER()` over `payload_digest` with a fixed `ORDER BY` on the same fields. If occurrence > 1:

   ```text
   event_sk = 'SYN-' || payload_digest || '-D' || occurrence
   ```

   Otherwise:

   ```text
   event_sk = 'SYN-' || payload_digest
   ```

### Excluded from the hash (by design)

- `ingested_at` — ingestion metadata; not required for business identity and could vary on re-ingestion.
- Derived Silver columns (`event_category`, `has_deal_context`, date truncations).

### Determinism

Same raw/bronze inputs → same `event_sk` values on every Silver run. Verified by repeated load + transform tests on a temporary database.

## Collision handling

- **SHA-256** digest space makes accidental collisions negligible.
- Tests assert `COUNT(*) = COUNT(DISTINCT event_sk)` on the full Silver/Gold event set.
- If two rows share an identical canonical payload, **`-D{n}`** suffixes disambiguate deterministically.

Current snapshot: **0** duplicate canonical payload groups among non-test raw events; suffix logic is defensive for future data.

## Validation results (WS-3)

Run via:

```bash
python -m pytest tests/test_event_identity.py -q
```

Checks include: non-null unique `event_sk`, preserved `event_id` nulls, unchanged row counts (60552 Silver / same Gold fact count), determinism across two Silver runs, no hash collisions.

## Known limitations

- **`event_sk` is internal** — do not send `SRC-*` / `SYN-*` values back to source systems.
- **Null `account_id`** rows remain in Silver (641 rows); WS-3 does not quarantine them.
- **Aggregated Gold fact** (`gold_fact_product_events_aggregated`) groups by normalized event name; it does not expose row-level `event_sk` (see `docs/event_taxonomy.md`).
- **Activation logic** still keys on account, deal dates, and `HasDealContext`; not on `EventId` / `EventSk`.
