import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db_config import connect_duckdb

con = connect_duckdb()

con.execute("""
CREATE OR REPLACE TABLE silver_geography AS

WITH base AS (

    SELECT
        UPPER(TRIM(country_code)) AS country_code,
        country_name,
        region,
        market,
        currency,
        sales_region
    FROM bronze_geography

),

deduped AS (

    SELECT
        *,
        ROW_NUMBER() OVER(
            PARTITION BY country_code
            ORDER BY country_name
        ) rn
    FROM base

)

SELECT
    country_code,
    country_name,
    region,

    CASE
        WHEN country_code = 'UK'
             AND market IS NULL
        THEN 'UK'
        ELSE market
    END AS market,

    currency,
    sales_region

FROM deduped
WHERE rn = 1
""")

print("✅ Created silver_geography")

con.close()