import duckdb
import os

con = duckdb.connect(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "product_analytics_light.db"
    )
)

con.execute("""
CREATE OR REPLACE TABLE gold_dim_geography AS
SELECT

    country_code AS CountryCode,
    country_name AS CountryName,
    region       AS Region,
    market       AS Market,
    sales_region AS SalesRegion,
    currency     AS Currency

FROM silver_geography
ORDER BY CountryCode
""")

print("✅ Created gold_dim_geography")

con.close()