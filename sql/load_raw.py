"""
Load raw__* tables from data/source_snapshot Parquet files into DuckDB.

Idempotent: each run replaces raw tables from snapshots after validation.
Uses staging tables so a failed load does not leave partially updated raw tables.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent))
from db_config import connect_duckdb, get_db_path, get_repo_root  # noqa: E402

SNAPSHOT_DIR_NAME = "source_snapshot"
MANIFEST_FILENAME = "MANIFEST.json"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_manifest(snapshot_dir: Path) -> dict:
    manifest_path = snapshot_dir / MANIFEST_FILENAME
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Missing manifest: {manifest_path}")
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def _describe_parquet(con: duckdb.DuckDBPyConnection, parquet_path: Path) -> list[tuple[str, str]]:
    rows = con.execute(
        f"DESCRIBE SELECT * FROM read_parquet('{parquet_path.as_posix()}')"
    ).fetchall()
    return [(row[0], row[1]) for row in rows]


def _null_counts(con: duckdb.DuckDBPyConnection, table: str, columns: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for column in columns:
        counts[column] = con.execute(
            f'SELECT COUNT(*) FROM {table} WHERE "{column}" IS NULL'
        ).fetchone()[0]
    return counts


def _validate_parquet_against_manifest(
    con: duckdb.DuckDBPyConnection,
    parquet_path: Path,
    entry: dict,
) -> None:
    expected_sha = entry["sha256"]
    actual_sha = _sha256_file(parquet_path)
    if actual_sha != expected_sha:
        raise ValueError(
            f"Checksum mismatch for {parquet_path.name}: "
            f"expected {expected_sha}, got {actual_sha}"
        )

    expected_cols = entry["columns"]
    expected_types = entry["column_types"]
    actual_schema = _describe_parquet(con, parquet_path)
    actual_cols = [name for name, _ in actual_schema]

    if actual_cols != expected_cols:
        raise ValueError(
            f"Column order/name mismatch for {parquet_path.name}: "
            f"expected {expected_cols}, got {actual_cols}"
        )

    actual_type_map = dict(actual_schema)
    for name in expected_cols:
        expected_dtype = expected_types[name]
        actual_dtype = actual_type_map[name]
        if actual_dtype.upper() != expected_dtype.upper():
            raise ValueError(
                f"Type mismatch for {parquet_path.name}.{name}: "
                f"expected {expected_dtype}, got {actual_dtype}"
            )

    parquet_sql = parquet_path.as_posix()
    row_count = con.execute(
        f"SELECT COUNT(*) FROM read_parquet('{parquet_sql}')"
    ).fetchone()[0]
    if row_count != entry["row_count"]:
        raise ValueError(
            f"Row count mismatch for {parquet_path.name}: "
            f"expected {entry['row_count']}, got {row_count}"
        )


def load_raw_tables(
    *,
    snapshot_dir: Path,
    db_path: Path | None = None,
) -> dict:
    snapshot_dir = snapshot_dir.resolve()
    manifest = load_manifest(snapshot_dir)

    if db_path is not None:
        os.environ["PULSEIQ_DB_PATH"] = str(db_path.resolve())

    target_db = get_db_path()
    target_db.parent.mkdir(parents=True, exist_ok=True)

    con = connect_duckdb()
    try:
        con.execute("BEGIN TRANSACTION")

        for entry in manifest["tables"]:
            table = entry["source_table"]
            parquet_path = snapshot_dir / entry["filename"]
            if not parquet_path.is_file():
                raise FileNotFoundError(f"Missing snapshot file: {parquet_path}")

            _validate_parquet_against_manifest(con, parquet_path, entry)

            staging = f"{table}__staging"
            parquet_sql = parquet_path.as_posix()
            con.execute(f"DROP TABLE IF EXISTS {staging}")
            con.execute(
                f"""
                CREATE TABLE {staging} AS
                SELECT * FROM read_parquet('{parquet_sql}')
                """
            )

            loaded_count = con.execute(f"SELECT COUNT(*) FROM {staging}").fetchone()[0]
            if loaded_count != entry["row_count"]:
                raise ValueError(
                    f"Staging row count mismatch for {table}: "
                    f"expected {entry['row_count']}, got {loaded_count}"
                )

            null_counts = _null_counts(con, staging, entry["columns"])
            if null_counts != entry["null_counts"]:
                raise ValueError(
                    f"Null count mismatch for {table}: "
                    f"expected {entry['null_counts']}, got {null_counts}"
                )

            con.execute(f"DROP TABLE IF EXISTS {table}")
            con.execute(f"ALTER TABLE {staging} RENAME TO {table}")

        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise
    finally:
        con.close()

    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Load raw__* tables from Parquet snapshots.")
    parser.add_argument(
        "--snapshot-dir",
        type=Path,
        default=None,
        help="Snapshot directory (default: data/source_snapshot).",
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=None,
        help="Target DuckDB path (overrides PULSEIQ_DB_PATH / default).",
    )
    args = parser.parse_args()

    snapshot_dir = args.snapshot_dir or (get_repo_root() / "data" / SNAPSHOT_DIR_NAME)

    try:
        manifest = load_raw_tables(snapshot_dir=snapshot_dir, db_path=args.db_path)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Load failed: {exc}", file=sys.stderr)
        return 1

    print(f"Loaded {len(manifest['tables'])} raw tables into {get_db_path()}")
    for entry in manifest["tables"]:
        print(f"  {entry['source_table']}: {entry['row_count']} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
