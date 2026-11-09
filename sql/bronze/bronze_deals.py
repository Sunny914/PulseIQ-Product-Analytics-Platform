import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db_config import connect_duckdb

con = connect_duckdb()

con.execute("""
CREATE OR REPLACE TABLE bronze_deals AS
SELECT
    deal_id,
    account_id,
    owner_user_id,
    pipeline_id,
    current_stage_id,
    status,
    created_at,
    closed_at,
    last_stage_changed_at,
    amount,
    currency,
    country_code,
    source_system
FROM raw__deals;
""")

print("✅ Created bronze_deals table")

con.close()