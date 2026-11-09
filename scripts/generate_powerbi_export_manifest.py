"""
Generate JSON manifest for Power BI CSV handoff (read-only validation).
"""
from __future__ import annotations

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import duckdb

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "sql"))
from gold_table_schemas import GOLD_TABLE_CSV_FILENAMES  # noqa: E402

PBI_TABLES = [
    "gold_dim_accounts",
    "gold_dim_users",
    "gold_dim_geography",
    "gold_fact_advanced_activation",
    "gold_fact_activation_as_of",
    "gold_fact_engagement_periodic",
    "gold_fact_feature_adoption_account",
    "gold_fact_feature_adoption_user",
    "gold_fact_feature_breadth_account",
    "gold_fact_feature_breadth_user",
    "gold_fact_product_activity_recency_account",
    "gold_fact_retention_cohort",
    "gold_fact_account_workflow_funnel",
    "gold_fact_segment_product_metrics",
]


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--export-dir", type=Path, required=True)
    parser.add_argument("--db-path", type=Path, required=True)
    parser.add_argument("--as-of-date", default="2026-07-11")
    args = parser.parse_args()

    export_dir = args.export_dir.resolve()
    db_path = args.db_path.resolve()
    con = duckdb.connect(str(db_path), read_only=True)

    tables = []
    for table in PBI_TABLES:
        csv_name = GOLD_TABLE_CSV_FILENAMES[table]
        csv_path = export_dir / csv_name
        entry = {"gold_table": table, "csv_file": csv_name, "present": csv_path.is_file()}
        if csv_path.is_file():
            with csv_path.open(newline="", encoding="utf-8") as handle:
                header = next(csv.reader(handle))
                row_count = sum(1 for _ in csv.reader(handle))
            db_cols = [r[0] for r in con.execute(f'DESCRIBE "{table}"').fetchall()]
            entry["columns"] = header
            entry["column_match"] = header == db_cols
            entry["row_count"] = row_count
            entry["db_row_count"] = con.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
            entry["row_count_match"] = row_count == entry["db_row_count"]
        tables.append(entry)

    con.close()
    manifest = {
        "manifest_version": "1.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "report_as_of_date": args.as_of_date,
        "export_directory": str(export_dir),
        "database_path": str(db_path),
        "synthetic_disclosure": "PulseIQ uses fictional B2B SaaS CRM synthetic data only.",
        "reporting_contexts": ["FULL_DATASET", "AS_OF"],
        "tables": tables,
    }
    out = export_dir / "POWERBI_EXPORT_MANIFEST.json"
    out.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Wrote {out}")
    return 0 if all(t.get("row_count_match", False) for t in tables if t["present"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
