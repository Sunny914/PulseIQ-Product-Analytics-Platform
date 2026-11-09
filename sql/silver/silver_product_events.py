import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db_config import connect_duckdb
from account_resolution_sql import (
    ACCOUNT_RESOLUTION_COLUMNS,
    DEAL_ACCOUNT_UNAMBIGUOUS_CTE,
    USER_ACCOUNT_MAP_CTE,
    VALID_ACCOUNTS_CTE,
)
from event_name_aliases import event_name_normalized_sql
from event_properties_sql import (
    EVENT_PROPERTIES_EXTRACT_COLUMNS_SQL,
    EVENT_PROPERTIES_JSON_COLUMN_SQL,
    EVENT_PROPERTIES_PARSE_STATUS_SQL,
)
from event_sk_sql import EVENT_PAYLOAD_DIGEST_SQL, EVENT_SK_EXPRESSION_SQL

EVENT_NAME_NORMALIZED_SQL = event_name_normalized_sql("event_name")

con = connect_duckdb()

con.execute(f"""

CREATE OR REPLACE TABLE silver_product_events AS

WITH base AS (

    SELECT
        event_id,
        event_name,
        user_id,
        account_id,
        deal_id,

        event_timestamp,
        ingested_at,
        event_date,

        platform,
        device_type,
        app_version,

        UPPER(country_code)
            AS country_code,

        event_properties,
        is_test_event,
        source_system

    FROM bronze_product_events
    WHERE is_test_event = FALSE

),

with_normalized AS (

    SELECT
        base.*,
        {EVENT_NAME_NORMALIZED_SQL} AS event_name_normalized
    FROM base

),

enriched AS (

    SELECT
        *,

        CAST(event_timestamp AS DATE)
            AS event_ts_date,

        DATE_TRUNC(
            'month',
            event_timestamp
        ) AS event_ts_month,

        CASE

            WHEN lower(event_name_normalized) LIKE '%login%'
                 THEN 'AUTH'

            WHEN lower(event_name_normalized) LIKE '%pipeline%'
              OR lower(event_name_normalized) LIKE '%deal%'
                 THEN 'PIPELINE'

            WHEN lower(event_name_normalized) LIKE '%activity%'
              OR lower(event_name_normalized) LIKE '%call%'
              OR lower(event_name_normalized) LIKE '%email%'
                 THEN 'ACTIVITY'

            WHEN lower(event_name_normalized) LIKE '%workflow%'
              OR lower(event_name_normalized) LIKE '%automation%'
                 THEN 'AUTOMATION'

            ELSE 'OTHER'

        END AS event_category,

        CASE
            WHEN deal_id IS NOT NULL
            THEN TRUE
            ELSE FALSE
        END AS has_deal_context

    FROM with_normalized
),

with_digest AS (

    SELECT
        enriched.*,
        {EVENT_PAYLOAD_DIGEST_SQL} AS payload_digest
    FROM enriched
),

with_occurrence AS (

    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY payload_digest
            ORDER BY
                event_timestamp,
                event_name,
                user_id,
                account_id,
                deal_id,
                event_properties,
                source_system,
                platform,
                device_type,
                app_version,
                country_code
        ) AS payload_occurrence
    FROM with_digest
),

{VALID_ACCOUNTS_CTE}

{DEAL_ACCOUNT_UNAMBIGUOUS_CTE}

{USER_ACCOUNT_MAP_CTE}

with_attribution AS (

    SELECT
        w.*,
        {EVENT_SK_EXPRESSION_SQL} AS event_sk,
        CASE
            WHEN w.event_id IS NOT NULL THEN 'SOURCE'
            ELSE 'SURROGATE'
        END AS event_sk_type,
        {ACCOUNT_RESOLUTION_COLUMNS}
    FROM with_occurrence AS w
    LEFT JOIN valid_accounts AS va
        ON w.account_id = va.account_id
    LEFT JOIN user_account_map AS um
        ON w.user_id = um.user_id
    LEFT JOIN deal_account_unambiguous AS da
        ON w.deal_id = da.deal_id
),

with_parsed_properties AS (

    SELECT
        wa.*,
        {EVENT_PROPERTIES_JSON_COLUMN_SQL},
        {EVENT_PROPERTIES_PARSE_STATUS_SQL}
    FROM with_attribution AS wa
)

SELECT
    event_sk,
    event_sk_type,

    event_id,
    event_name,
    event_name_normalized,
    event_category,

    user_id,
    account_id,
    account_id_resolved,
    account_resolution_status,
    account_resolution_method,
    account_resolution_reason,
    deal_id,
    has_deal_context,

    event_timestamp,
    event_ts_date,
    event_ts_month,

    ingested_at,
    event_date,

    platform,
    device_type,
    app_version,
    country_code,

    event_properties,
    event_properties_parse_status,
    {EVENT_PROPERTIES_EXTRACT_COLUMNS_SQL},
    source_system

FROM with_parsed_properties
""")

con.execute("""
CREATE OR REPLACE VIEW silver_product_events_quarantine AS
SELECT *
FROM silver_product_events
WHERE account_resolution_status = 'QUARANTINED'
""")

print("✅ Created silver_product_events")
print("✅ Created view silver_product_events_quarantine")

con.close()