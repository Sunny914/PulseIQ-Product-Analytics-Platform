# PulseIQ — Event Taxonomy & Normalized Names

## Original event inventory (non-test raw)

Verified against `raw__product_events` (reference database, read-only audit).

| Original `event_name` | Frequency |
|----------------------|----------:|
| enable_automation | 12,159 |
| log_activity | 12,135 |
| move_deal_stage | 12,103 |
| create_deal | 12,053 |
| invite_user | 3,997 |
| view_dashboard | 3,984 |
| login | 3,861 |
| ViewDashboard | 118 |
| Login | 83 |
| user_login | 59 |

Silver row count after test filter: **60,552** (unchanged by normalization).

## Canonical taxonomy (normalized names)

After explicit alias mapping, **seven** canonical event names remain:

| `event_name_normalized` | Role in product |
|-------------------------|-----------------|
| enable_automation | Automation / workflow setup |
| log_activity | CRM activity logging |
| move_deal_stage | Pipeline stage change |
| create_deal | Deal creation |
| invite_user | Team / onboarding invite |
| view_dashboard | Dashboard engagement |
| login | Authentication / session |

## Alias mapping (explicit only)

Defined in `sql/event_name_aliases.py`:

| Original | Normalized | Rationale |
|----------|------------|-----------|
| ViewDashboard | view_dashboard | Same action; PascalCase ingestion alias. Platforms/sources match `view_dashboard` (web/mobile/automation/backend). |
| Login | login | Same action; case-sensitive categorization previously misclassified `Login` as OTHER. Feature mix (dashboard, deal, pipeline, automation) aligns with `login`. |
| user_login | login | Same feature_name distribution pattern as `login`; same AUTH semantics; distinct string is legacy alias only. |

**Not merged:** All other names are already canonical snake_case verbs. No evidence that distinct names (e.g. `create_deal` vs `move_deal_stage`) represent the same action.

## Ambiguous / unmapped events

- **None** requiring separate handling beyond the three aliases above.
- Unknown future names pass through: `event_name_normalized = event_name`.

## Event category definitions

Applied to **`event_name_normalized`** (case-insensitive patterns):

| Category | Rule (summary) |
|----------|----------------|
| AUTH | Name contains `login` |
| PIPELINE | Name contains `pipeline` or `deal` |
| ACTIVITY | Name contains `activity`, `call`, or `email` |
| AUTOMATION | Name contains `workflow` or `automation` |
| OTHER | Default |

**WS-4 category correction:** `Login` (83 rows) becomes AUTH via normalization to `login`. `ViewDashboard` remains OTHER (same as `view_dashboard`).

## Column model

| Column | Layer | Purpose |
|--------|--------|---------|
| `event_name` | Silver / Gold `EventName` | **Original** source string |
| `event_name_normalized` | Silver / Gold `EventNameNormalized` | **Canonical** name for reporting |
| `event_category` | Silver / Gold | Derived from normalized name |

`event_sk` (WS-3) continues to use **original** `event_name` in its hash payload so existing surrogate keys remain stable.

## Aggregation behavior

`gold_fact_product_events_aggregated` groups by:

- `EventDate`, `EventNameNormalized`, `EventCategory`, `AccountId`

`SourceEventNames` lists distinct original `event_name` values in each group for traceability.

**Row count impact:** Aggregated groups **decrease** when aliases share the same date, account, and category (e.g. `login` + `Login` + `user_login`). Detail fact row count is unchanged.

## Data-quality considerations

- Normalization does **not** fix null `account_id` or null `event_id` (later workstreams).
- Deal-related names (`create_deal`, `move_deal_stage`) stay PIPELINE; do not collapse into one event.
- Dashboard views remain separate from login for funnel design.

## Product analytics examples

- **Funnel:** `invite_user` → `login` → `view_dashboard` → `create_deal` using `EventNameNormalized`.
- **Activation support:** Pipeline events unchanged; categories consistent for `login` variants.
- **Feature adoption:** Pair with WS-6 `feature_name` from JSON when available.
- **Engagement / DAU:** Aggregate on `EventNameNormalized` + `UniqueUsers` from the aggregated fact.
- **Retention:** Session grain still `event_sk`; trend metrics use normalized names.
