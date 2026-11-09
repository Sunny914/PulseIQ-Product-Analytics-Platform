# Feature properties and adoption analytics (WS-6)

## Event property inventory (snapshot-backed Silver, n=60,552)

| Metric | Value |
|--------|------:|
| NULL `event_properties` | 0 |
| Valid JSON (`TRY_CAST` succeeds) | 60,552 |
| Invalid JSON | 0 |
| Rows with `feature_name` | 60,552 |
| Rows missing `feature_name` (valid JSON) | 0 |
| Rows with JSON `source` (`EventSource`) | 60,552 |
| Rows with `pipeline_id` | 24,156 |
| Rows with `stage_id` | 24,156 |

**JSON keys observed:** `feature_name`, `source`, `pipeline_id` (conditional), `stage_id` (conditional). No other keys appear in the current corpus.

### `feature_name` taxonomy (product feature area)

| feature_name | Event rows |
|--------------|----------:|
| dashboard | 15,236 |
| pipeline | 15,220 |
| automation | 15,200 |
| deal | 14,896 |

### JSON `source` (`EventSource` in Gold)

| EventSource | Event rows |
|-------------|----------:|
| automation | 20,201 |
| api | 20,185 |
| ui | 20,166 |

Distinct from **`SourceSystem`** (ingestion/system column on the event row).

### Pipeline / stage coverage

- **24,156** events carry both `pipeline_id` and `stage_id` (typically pipeline-category interactions).
- **36,396** events have no pipeline/stage properties (feature usage outside an explicit pipeline stage context).

## Property definitions

| Field | Layer | Description |
|-------|--------|-------------|
| `event_properties` | Silver / Gold `EventProperties` | Original JSON payload (unchanged string) |
| `event_properties_parse_status` | Silver / Gold `EventPropertiesParseStatus` | `OK`, `NULL_PAYLOAD`, or `INVALID_JSON` |
| `feature_name` | Silver / Gold `FeatureName` | Product feature area from JSON |
| `event_source` | Silver / Gold `EventSource` | Client/API/automation surface from JSON `source` |
| `pipeline_id` | Silver / Gold `PipelineId` | CRM pipeline identifier when present |
| `stage_id` | Silver / Gold `StageId` | Pipeline stage identifier when present |

## Extraction logic

Implemented once in **`sql/event_properties_sql.py`**, applied in **`silver_product_events`** (`with_parsed_properties` CTE):

1. `TRY_CAST(event_properties AS JSON)` → `event_properties_json`
2. Parse status derived from NULL payload vs failed cast
3. When status = `OK`, `json_extract_string` for each key; otherwise extracted columns are **NULL** (payload still preserved)

Gold detail and aggregated facts read typed Silver columns (no second parse in Gold SQL).

## Aggregated Gold grain (WS-6)

**Group by:** `EventDate`, `EventNameNormalized`, `EventCategory`, **`FeatureName`**, **`AccountId`** (source account semantics unchanged from WS-5.2).

| Version | Aggregated row groups | SUM(EventCount) |
|---------|----------------------:|----------------:|
| Pre-WS-6 (no FeatureName) | 30,797 | 60,552 |
| WS-6 (with FeatureName) | **49,300** | **60,552** |

Adding `FeatureName` splits groups where the same date/event/account combination spans multiple feature areas; event grain is not multiplied.

## Adoption vs usage metrics

| Metric type | Definition | Example |
|-------------|------------|---------|
| **Usage volume** | Event counts or event-weighted totals | `SUM(EventCount)` from aggregated fact |
| **Adopted users** | **Distinct** `UserId` with ≥1 qualifying event | `COUNT(DISTINCT UserId)` |
| **Adopted accounts** | **Distinct** `AccountId` or resolved account with ≥1 event | `COUNT(DISTINCT AccountIdResolved)` |
| **Adoption rate** | Adopted entities ÷ eligible population | Adopted accounts ÷ active accounts |

A user with 100 events counts as **one** adopted user, not 100.

For conservative reporting, filter `AccountResolutionStatus = 'SOURCE_VERIFIED'` and use `AccountId`. For enriched coverage, use `AccountIdResolved` and include `ENRICHED` where policy allows (see `docs/orphan_events.md`).

## Example SQL

### A. Feature adoption by feature_name (distinct users)

```sql
SELECT
    FeatureName,
    COUNT(DISTINCT UserId) AS adopted_users,
    COUNT(*) AS event_rows
FROM gold_fact_product_events
WHERE FeatureName IS NOT NULL
GROUP BY FeatureName
ORDER BY adopted_users DESC;
```

### B. Feature usage by account (volume + adopted-user count)

```sql
SELECT
    AccountId,
    FeatureName,
    COUNT(*) AS event_rows,
    COUNT(DISTINCT UserId) AS active_users
FROM gold_fact_product_events
WHERE AccountResolutionStatus IN ('SOURCE_VERIFIED', 'ENRICHED')
GROUP BY AccountId, FeatureName;
```

### C. Feature usage by user

```sql
SELECT
    UserId,
    FeatureName,
    COUNT(*) AS event_rows,
    MIN(EventTimestamp) AS first_use_at,
    MAX(EventTimestamp) AS last_use_at
FROM gold_fact_product_events
GROUP BY UserId, FeatureName;
```

### D. Feature adoption by account segment

```sql
SELECT
    a.Segment,
    e.FeatureName,
    COUNT(DISTINCT e.AccountIdResolved) AS adopted_accounts,
    COUNT(DISTINCT e.UserId) AS adopted_users
FROM gold_fact_product_events e
INNER JOIN gold_dim_accounts a
    ON e.AccountIdResolved = a.AccountId
WHERE e.AccountIdResolved IS NOT NULL
GROUP BY a.Segment, e.FeatureName;
```

### E. Feature usage trends over time

```sql
SELECT
    EventDate,
    FeatureName,
    SUM(EventCount) AS events,
    SUM(UniqueUsers) AS summed_unique_users  -- not global distinct; use detail for strict DAU
FROM gold_fact_product_events_aggregated
GROUP BY EventDate, FeatureName
ORDER BY EventDate, FeatureName;
```

For strict daily distinct users, query detail:

```sql
SELECT EventDate, FeatureName, COUNT(DISTINCT UserId) AS daily_active_users
FROM gold_fact_product_events
GROUP BY EventDate, FeatureName;
```

### F. Pipeline–stage interaction

```sql
SELECT
    PipelineId,
    StageId,
    FeatureName,
    COUNT(*) AS event_rows,
    COUNT(DISTINCT UserId) AS users,
    COUNT(DISTINCT AccountIdResolved) AS accounts
FROM gold_fact_product_events
WHERE PipelineId IS NOT NULL AND StageId IS NOT NULL
GROUP BY PipelineId, StageId, FeatureName;
```

## Known limitations

- Current dataset has **no** invalid JSON; `INVALID_JSON` path is tested but not populated in production snapshots.
- `pipeline_id` / `stage_id` are not present on all events.
- Aggregated `UniqueUsers` is distinct **within** each group; summing across groups overstates global distinct users.
- **`AccountId`** in aggregated Gold remains **source** account (null for orphans); use detail + `AccountIdResolved` for enriched account rollups.

## WS-12 Gold feature analytics

| Table | Grain |
|-------|--------|
| `gold_fact_feature_adoption_account` | Account × Feature × ReportContext × AttributionPopulation |
| `gold_fact_feature_adoption_user` | User × Feature × ReportContext × AttributionPopulation |
| `gold_fact_feature_adoption_by_period` | Calendar month × Feature × EntityType (distinct per period) |
| `gold_fact_feature_breadth_account` / `_user` | Entity × ReportContext; buckets `narrow_1_feature`, `moderate_2_features`, `broad_3plus_features` |

**Adoption** = at least one qualifying event (`HasAdoptedFeature = TRUE`). **Repeat usage** = `IsRepeatFeatureUsage` / `FeatureEventCount > 1`. **Usage volume** = `FeatureEventCount` — not labelled adoption.

Official account adoption uses SOURCE_VERIFIED + `AccountId`. User adoption uses SOURCE_VERIFIED + non-null `UserId`. Sensitivity rows are labelled separately in Gold.

## Future analytics opportunities (not implemented in WS-6 / beyond WS-12)

- Feature adoption funnels (first use → repeat use within 7/28 days)
- Feature mix per account (penetration of dashboard vs automation)
- Join `PipelineId` / `StageId` to a pipeline dimension when available
- Property-level DQ alerts on rising `INVALID_JSON` or missing `feature_name`
