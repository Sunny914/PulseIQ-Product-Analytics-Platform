import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db_config import connect_duckdb

con = connect_duckdb()

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