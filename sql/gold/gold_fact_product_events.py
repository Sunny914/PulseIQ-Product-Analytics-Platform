import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db_config import connect_duckdb

con = connect_duckdb()

con.execute("""
CREATE OR REPLACE TABLE gold_fact_product_events AS
SELECT

    event_sk        AS EventSk,
    event_id        AS EventId,

    account_id      AS AccountId,
    account_id_resolved AS AccountIdResolved,
    account_resolution_status AS AccountResolutionStatus,
    account_resolution_method AS AccountResolutionMethod,
    account_resolution_reason AS AccountResolutionReason,
    user_id         AS UserId,
    deal_id         AS DealId,

    event_name              AS EventName,
    event_name_normalized   AS EventNameNormalized,
    event_category          AS EventCategory,
    has_deal_context AS HasDealContext,

    event_timestamp AS EventTimestamp,
    event_ts_date   AS EventDate,
    event_ts_month  AS EventMonth,

    event_properties AS EventProperties,
    event_properties_parse_status AS EventPropertiesParseStatus,
    feature_name    AS FeatureName,
    event_source    AS EventSource,
    pipeline_id     AS PipelineId,
    stage_id        AS StageId,

    platform        AS Platform,
    device_type     AS DeviceType,
    app_version     AS AppVersion,
    country_code    AS CountryCode,

    source_system   AS SourceSystem

FROM silver_product_events
ORDER BY EventSk
""")

print("✅ Created gold_fact_product_events")

con.close()