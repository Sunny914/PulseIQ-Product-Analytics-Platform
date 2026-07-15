import duckdb
import os
import pandas as pd

con = duckdb.connect(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "product_analytics_light.db"
    )
)

# Read Excel file
excel_path = os.path.join(
    os.path.dirname(__file__),
    "..",
    "data",
    "raw_geography.xlsx"
)

df = pd.read_excel(excel_path)

# Register dataframe as temporary view
con.register("raw_geography_df", df)

# Create Bronze table
con.execute("""
CREATE OR REPLACE TABLE bronze_geography AS
SELECT
    country_code,
    country_name,
    region,
    market,
    currency,
    sales_region
FROM raw_geography_df;
""")

print("✅ Created bronze_geography table")

con.close()