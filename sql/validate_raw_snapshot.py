"""
Validate Parquet raw snapshots against MANIFEST.json.

Can run without loading into DuckDB (checksum, schema via read_parquet).
Optional --db-path compares a loaded database to the manifest.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent))
from db_config import connect_duckdb, get_repo_root  # noqa: E402

MANIFEST_FILENAME = "MANIFEST.json"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_snapshot_files(snapshot_dir: Path) -> list[str]:
    errors: list[str] = []
    manifest_path = snapshot_dir / MANIFEST_FILENAME
    if not manifest_path.is_file():
        return [f"Missing {manifest_path}"]

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    con = duckdb.connect()

    try:
        for entry in manifest["tables"]:
            filename = entry["filename"]
            parquet_path = snapshot_dir / filename
            table = entry["source_table"]

            if not parquet_path.is_file():
                errors.append(f"Missing snapshot file: {parquet_path}")
                continue

            actual_sha = _sha256_file(parquet_path)
            if actual_sha != entry["sha256"]:
                errors.append(f"{filename}: SHA-256 mismatch")

            if parquet_path.stat().st_size != entry["file_size_bytes"]:
                errors.append(f"{filename}: file size mismatch")

            parquet_sql = parquet_path.as_posix()
            schema = con.execute(
                f"DESCRIBE SELECT * FROM read_parquet('{parquet_sql}')"
            ).fetchall()
            columns = [row[0] for row in schema]
            if columns != entry["columns"]:
                errors.append(f"{filename}: column list mismatch")

            row_count = con.execute(
                f"SELECT COUNT(*) FROM read_parquet('{parquet_sql}')"
            ).fetchone()[0]
            if row_count != entry["row_count"]:
                errors.append(
                    f"{filename}: row count {row_count} != manifest {entry['row_count']}"
                )

            for column in entry["columns"]:
                null_count = con.execute(
                    f"""
                    SELECT COUNT(*) FROM read_parquet('{parquet_sql}')
                    WHERE "{column}" IS NULL
                    """
                ).fetchone()[0]
                if null_count != entry["null_counts"][column]:
                    errors.append(
                        f"{filename}.{column}: null count {null_count} != "
                        f"manifest {entry['null_counts'][column]}"
                    )

            # Identifier preservation checks (non-null distinct counts)
            primary_id = entry["business_identifiers"][0]
            if primary_id in entry["columns"]:
                distinct_non_null = con.execute(
                    f"""
                    SELECT COUNT(DISTINCT "{primary_id}")
                    FROM read_parquet('{parquet_sql}')
                    WHERE "{primary_id}" IS NOT NULL
                    """
                ).fetchone()[0]
                expected_distinct = (
                    entry["row_count"]
                    - entry["null_counts"].get(primary_id, 0)
                    - entry.get("duplicate_identifier_rows", 0)
                )
                if distinct_non_null != expected_distinct:
                    errors.append(
                        f"{filename}: distinct {primary_id}={distinct_non_null}, "
                        f"expected {expected_distinct}"
                    )

            # Timestamp preservation spot check: min/max present
            for date_col in entry.get("date_columns", []):
                if date_col not in entry["columns"]:
                    continue
                min_max = con.execute(
                    f"""
                    SELECT MIN("{date_col}"), MAX("{date_col}")
                    FROM read_parquet('{parquet_sql}')
                    """
                ).fetchone()
                if min_max[0] is None and entry["null_counts"].get(date_col, 0) < entry["row_count"]:
                    errors.append(f"{filename}.{date_col}: unexpected all-null timestamps")

        # Known raw DQ counts
        events_entry = next(
            (e for e in manifest["tables"] if e["source_table"] == "raw__product_events"),
            None,
        )
        if events_entry:
            if events_entry["null_counts"].get("event_id") != 625:
                errors.append("raw__product_events: expected 625 null event_id in manifest")
            if events_entry["null_counts"].get("account_id") != 653:
                errors.append("raw__product_events: expected 653 null account_id in manifest")

    finally:
        con.close()

    return errors


def validate_loaded_db(manifest: dict) -> list[str]:
    errors: list[str] = []
    con = connect_duckdb(read_only=True)
    try:
        for entry in manifest["tables"]:
            table = entry["source_table"]
            row_count = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            if row_count != entry["row_count"]:
                errors.append(f"{table}: loaded row count {row_count} != manifest")

            for column, expected_nulls in entry["null_counts"].items():
                null_count = con.execute(
                    f'SELECT COUNT(*) FROM {table} WHERE "{column}" IS NULL'
                ).fetchone()[0]
                if null_count != expected_nulls:
                    errors.append(
                        f"{table}.{column}: null count {null_count} != manifest {expected_nulls}"
                    )
    finally:
        con.close()
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate raw Parquet snapshots.")
    parser.add_argument(
        "--snapshot-dir",
        type=Path,
        default=None,
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=None,
        help="If set, also validate loaded raw tables in this database.",
    )
    args = parser.parse_args()

    snapshot_dir = args.snapshot_dir or (get_repo_root() / "data" / "source_snapshot")

    errors = validate_snapshot_files(snapshot_dir)
    if args.db_path is not None:
        import os

        os.environ["PULSEIQ_DB_PATH"] = str(args.db_path.resolve())
        manifest = json.loads((snapshot_dir / MANIFEST_FILENAME).read_text(encoding="utf-8"))
        errors.extend(validate_loaded_db(manifest))

    if errors:
        for err in errors:
            print(f"FAIL: {err}", file=sys.stderr)
        return 1

    print(f"Validation passed for {snapshot_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
