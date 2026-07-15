import duckdb
import os

# Connect to DuckDB database
con = duckdb.connect(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "product_analytics_light.db"
    )
)

# Create Bronze Accounts Table
con.execute("""
CREATE OR REPLACE TABLE bronze_accounts AS
SELECT
    account_id,
    account_name,
    country_code,
    city,
    industry,
    employee_band,
    segment,
    created_at,
    trial_start_date,
    trial_end_date,
    account_status,
    acquisition_channel
FROM raw__accounts;
""")

print("✅ Created bronze_accounts table")

con.close()