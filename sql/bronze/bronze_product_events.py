import duckdb
import os

con = duckdb.connect(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "product_analytics_light.db"
    )
)

con.execute("""
CREATE OR REPLACE TABLE bronze_product_events AS
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
    country_code,
    event_properties,
    is_test_event,
    source_system
FROM raw__product_events;
""")

print("✅ Created bronze_product_events table")

con.close()