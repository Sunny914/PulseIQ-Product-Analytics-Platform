import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db_config import connect_duckdb

con = connect_duckdb()

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