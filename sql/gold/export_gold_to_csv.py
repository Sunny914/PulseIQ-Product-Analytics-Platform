import duckdb
import os
from pathlib import Path

# Resolve paths from this script's location so the script works no matter where it is launched from
script_dir = Path(__file__).resolve().parent
workspace_root = script_dir.parent.parent

action_dir = workspace_root / "exports" / "gold_csv"
db_path = workspace_root / "product_analytics_light.db"

# Connect to database
con = duckdb.connect(str(db_path))

# Output folder
output_folder = str(action_dir)
os.makedirs(output_folder, exist_ok=True)

# Gold tables
gold_tables = [
    "gold_dim_accounts",
    "gold_dim_geography",
    "gold_dim_users",
    "gold_fact_advanced_activation",
    "gold_fact_deals",
    "gold_fact_product_events",
    "gold_fact_product_events_aggregated"
]

for table in gold_tables:
    output_path = os.path.join(output_folder, f"{table}.csv")
    output_path = output_path.replace("\\", "/")

    con.execute(f"""
        COPY {table}
        TO '{output_path}'
        WITH (HEADER, DELIMITER ',');
    """)

    print(f"Exported {table}")

con.close()

print("All Gold tables exported successfully.")