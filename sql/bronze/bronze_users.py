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