import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db_config import connect_duckdb, get_repo_root
from gold_table_schemas import GOLD_TABLE_CSV_FILENAMES

export_override = os.environ.get("PULSEIQ_EXPORT_DIR")
action_dir = Path(export_override) if export_override else get_repo_root() / "exports" / "gold_csv"
con = connect_duckdb()

# Output folder
output_folder = str(action_dir)
os.makedirs(output_folder, exist_ok=True)

# Gold tables (override with comma-separated PULSEIQ_EXPORT_TABLES)
_default_gold_tables = [
    "gold_dim_accounts",
    "gold_dim_geography",
    "gold_dim_users",
    "gold_fact_advanced_activation",
     "gold_fact_activation_as_of",
    "gold_fact_deals",
    "gold_fact_product_events",
    "gold_fact_product_events_aggregated",
    "gold_fact_engagement_periodic",
    "gold_fact_feature_adoption_account",
    "gold_fact_feature_adoption_user",
    "gold_fact_feature_adoption_by_period",
    "gold_fact_feature_breadth_account",
    "gold_fact_feature_breadth_user",
    "gold_fact_product_activity_recency_account",
    "gold_fact_product_activity_recency_user",
    "gold_fact_qualified_product_events",
    "gold_fact_retention_cohort",
    "gold_fact_account_workflow_funnel",
    "gold_fact_segment_product_metrics",
]
_tables_env = os.environ.get("PULSEIQ_EXPORT_TABLES")
gold_tables = (
    [name.strip() for name in _tables_env.split(",") if name.strip()]
    if _tables_env
    else _default_gold_tables
)

existing = {
    row[0]
    for row in con.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
    ).fetchall()
}

for table in gold_tables:
    if table not in existing:
        print(f"Skipped {table} (not present in database)")
        continue
    csv_name = GOLD_TABLE_CSV_FILENAMES.get(table, f"{table}.csv")
    output_path = os.path.join(output_folder, csv_name)
    output_path = output_path.replace("\\", "/")

    con.execute(f"""
        COPY {table}
        TO '{output_path}'
        WITH (HEADER, DELIMITER ',');
    """)

    print(f"Exported {table}")

con.close()

print("All Gold tables exported successfully.")