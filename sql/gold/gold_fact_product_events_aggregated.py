import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db_config import connect_duckdb

con = connect_duckdb()

con.execute("""
CREATE OR REPLACE TABLE gold_fact_product_events_aggregated AS
SELECT

    event_ts_date                AS EventDate,
    event_name_normalized        AS EventNameNormalized,
    event_category               AS EventCategory,
    feature_name                 AS FeatureName,
    account_id                   AS AccountId,

    COUNT(*)                     AS EventCount,
    COUNT(DISTINCT user_id)      AS UniqueUsers,
    string_agg(DISTINCT event_name, ', ' ORDER BY event_name)
        AS SourceEventNames

FROM silver_product_events

GROUP BY
    event_ts_date,
    event_name_normalized,
    event_category,
    feature_name,
    account_id

ORDER BY
    EventDate,
    EventNameNormalized,
    FeatureName,
    AccountId
""")

print("✅ Created gold_fact_product_events_aggregated")

con.close()