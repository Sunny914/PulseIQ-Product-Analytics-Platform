import os
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db_config import connect_duckdb

con = connect_duckdb()

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