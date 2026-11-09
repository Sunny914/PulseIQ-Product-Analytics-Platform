"""
Export raw__* tables from the authoritative DuckDB into data/source_snapshot/ Parquet files.

Uses a read-only connection to the source database. Does not modify source data.
Run manually when refreshing snapshots from the reference database.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent))
from db_config import connect_duckdb, get_db_path, get_repo_root  # noqa: E402

SNAPSHOT_DIR_NAME = "source_snapshot"
MANIFEST_VERSION = "1.0"
SNAPSHOT_IDENTIFIER = "pulseiq-raw-v1"

RAW_TABLES: tuple[str, ...] = (
    "raw__accounts",
    "raw__users",
    "raw__deals",
    "raw__product_events",
)

TABLE_METADATA: dict[str, dict[str, list[str]]] = {
    "raw__accounts": {
        "business_identifiers": ["account_id"],
        "date_columns": ["created_at", "trial_start_date", "trial_end_date"],
    },
    "raw__users": {
        "business_identifiers": ["user_id", "account_id"],
        "date_columns": ["created_at", "last_seen_at"],
    },
    "raw__deals": {
        "business_identifiers": ["deal_id", "account_id", "owner_user_id"],
        "date_columns": ["created_at", "closed_at", "last_stage_changed_at"],
    },
    "raw__product_events": {
        "business_identifiers": ["event_id", "user_id", "account_id", "deal_id"],
        "date_columns": ["event_timestamp", "ingested_at", "event_date"],
    },
}


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _table_inventory(con, table: str) -> dict:
    cols_df = con.execute(f"DESCRIBE {table}").fetchdf()
    column_names = cols_df["column_name"].tolist()
    column_types = dict(zip(cols_df["column_name"], cols_df["column_type"]))
    row_count = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

    null_counts: dict[str, int] = {}
    for column in column_names:
        null_counts[column] = con.execute(
            f'SELECT COUNT(*) FROM {table} WHERE "{column}" IS NULL'
        ).fetchone()[0]

    id_cols = TABLE_METADATA[table]["business_identifiers"]
    primary_id = id_cols[0]
    duplicate_identifier_rows = con.execute(
        f"""
        SELECT COALESCE(COUNT(*) - COUNT(DISTINCT "{primary_id}"), 0)
        FROM {table}
        WHERE "{primary_id}" IS NOT NULL
        """
    ).fetchone()[0]

    return {
        "row_count": row_count,
        "columns": column_names,
        "column_types": column_types,
        "null_counts": null_counts,
        "duplicate_identifier_rows": duplicate_identifier_rows,
    }


def export_snapshots(source_db: Path, snapshot_dir: Path) -> dict:
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect(str(source_db), read_only=True)
    try:
        generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        table_entries: list[dict] = []

        for table in RAW_TABLES:
            filename = f"{table}.parquet"
            out_path = snapshot_dir / filename
            out_sql = out_path.as_posix()

            con.execute(
                f"""
                COPY (SELECT * FROM {table})
                TO '{out_sql}'
                (FORMAT PARQUET);
                """
            )

            inventory = _table_inventory(con, table)
            file_size = out_path.stat().st_size
            # Column types keyed by name (manifest JSON may sort keys; loaders match by name).
            ordered_types = {
                name: inventory["column_types"][name] for name in inventory["columns"]
            }
            entry = {
                "source_table": table,
                "filename": filename,
                "row_count": inventory["row_count"],
                "columns": inventory["columns"],
                "column_types": ordered_types,
                "null_counts": inventory["null_counts"],
                "business_identifiers": TABLE_METADATA[table]["business_identifiers"],
                "date_columns": TABLE_METADATA[table]["date_columns"],
                "duplicate_identifier_rows": inventory["duplicate_identifier_rows"],
                "file_size_bytes": file_size,
                "sha256": _sha256_file(out_path),
            }
            table_entries.append(entry)

        manifest = {
            "manifest_version": MANIFEST_VERSION,
            "snapshot_identifier": SNAPSHOT_IDENTIFIER,
            "snapshot_generated_at_utc": generated_at,
            "data_provenance": (
                "Exported from PulseIQ authoritative DuckDB raw__* tables; "
                "synthetic B2B SaaS CRM portfolio dataset."
            ),
            "source_database": {
                "absolute_path_at_export": str(source_db.resolve()),
                "snapshot_identifier": SNAPSHOT_IDENTIFIER,
            },
            "tables": table_entries,
            "geography_limitation": {
                "raw__geography_present_in_source": False,
                "original_file_expected": "sql/data/raw_geography.xlsx",
                "original_file_in_repository": False,
                "bronze_geography_rows_in_reference_db": None,
                "silver_geography_rows_in_reference_db": None,
                "gold_dim_geography_rows_in_reference_db": None,
                "reproducibility_note": (
                    "Geography is not included in this raw snapshot. "
                    "Bronze geography must be restored from the missing Excel file "
                    "or a separately documented reference export in a future workstream."
                ),
            },
            "known_data_quality_issues": [
                {
                    "table": "raw__product_events",
                    "issue": "null_event_id",
                    "count": 625,
                },
                {
                    "table": "raw__product_events",
                    "issue": "null_account_id",
                    "count": 653,
                },
                {
                    "table": "raw__deals",
                    "issue": "duplicate_deal_id_values",
                    "duplicate_identifier_rows": 35,
                },
            ],
        }

        # Enrich geography counts from reference DB when available
        for layer_table, key in [
            ("bronze_geography", "bronze_geography_rows_in_reference_db"),
            ("silver_geography", "silver_geography_rows_in_reference_db"),
            ("gold_dim_geography", "gold_dim_geography_rows_in_reference_db"),
        ]:
            try:
                manifest["geography_limitation"][key] = con.execute(
                    f"SELECT COUNT(*) FROM {layer_table}"
                ).fetchone()[0]
            except duckdb.Error:
                manifest["geography_limitation"][key] = None

        manifest_path = snapshot_dir / "MANIFEST.json"
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return manifest
    finally:
        con.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Export raw__* Parquet snapshots.")
    parser.add_argument(
        "--source-db",
        type=Path,
        default=None,
        help="Source DuckDB file (default: authoritative repo database).",
    )
    parser.add_argument(
        "--snapshot-dir",
        type=Path,
        default=None,
        help="Output directory (default: data/source_snapshot).",
    )
    args = parser.parse_args()

    source_db = (args.source_db or get_db_path()).resolve()
    snapshot_dir = (args.snapshot_dir or (get_repo_root() / "data" / SNAPSHOT_DIR_NAME)).resolve()

    if not source_db.is_file():
        print(f"Source database not found: {source_db}", file=sys.stderr)
        return 1

    export_snapshots(source_db, snapshot_dir)
    print(f"Exported {len(RAW_TABLES)} tables to {snapshot_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
