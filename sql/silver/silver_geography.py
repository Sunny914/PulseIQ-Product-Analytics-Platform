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