import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db_config import connect_duckdb

con = connect_duckdb()

con.execute("""
CREATE OR REPLACE TABLE bronze_users AS
SELECT
    user_id,
    account_id,
    full_name,
    email,
    job_role,
    user_status,
    created_at,
    last_seen_at,
    timezone,
    locale,
    is_admin
FROM raw__users;
""")

print("✅ Created bronze_users table")

con.close()