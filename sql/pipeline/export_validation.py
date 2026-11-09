"""Validate full Gold CSV export against DuckDB schemas and reconciliation."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

import duckdb

from gold_table_schemas import (
    GOLD_FACT_ACTIVATION_AS_OF_COLUMNS,
    GOLD_TABLE_CSV_FILENAMES,
)


@dataclass
class ExportValidationResult:
    passed: bool
    partial: bool
    errors: list[str] = field(default_factory=list)
    files_validated: list[str] = field(default_factory=list)


def validate_gold_exports(db_path: Path, export_dir: Path) -> ExportValidationResult:
    errors: list[str] = []
    files: list[str] = []
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        existing = {
            row[0]
            for row in con.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
            ).fetchall()
        }
        present_tables = [t for t in GOLD_TABLE_CSV_FILENAMES if t in existing]
        partial = len(present_tables) < len(GOLD_TABLE_CSV_FILENAMES)

        for table in GOLD_TABLE_CSV_FILENAMES:
            if table not in existing:
                errors.append(f"Missing Gold table in database: {table}")
                continue
            csv_name = GOLD_TABLE_CSV_FILENAMES[table]
            csv_path = export_dir / csv_name
            if not csv_path.is_file():
                errors.append(f"Missing export file: {csv_name}")
                continue

            with csv_path.open(newline="", encoding="utf-8") as handle:
                header = next(csv.reader(handle))
                row_count = sum(1 for _ in csv.reader(handle))

            db_cols = [row[0] for row in con.execute(f'DESCRIBE "{table}"').fetchall()]
            if header != db_cols:
                errors.append(f"Header mismatch for {table}")
            db_rows = con.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
            if row_count != db_rows:
                errors.append(f"Row count mismatch for {table}: csv {row_count} db {db_rows}")
            files.append(csv_name)

        if "gold_fact_activation_as_of" in existing:
            activation_csv = export_dir / GOLD_TABLE_CSV_FILENAMES["gold_fact_activation_as_of"]
            if activation_csv.is_file():
                with activation_csv.open(newline="", encoding="utf-8") as handle:
                    header = next(csv.reader(handle))
                for col in GOLD_FACT_ACTIVATION_AS_OF_COLUMNS:
                    if col not in header:
                        errors.append(f"Missing activation column in export: {col}")

        agg_csv = export_dir / GOLD_TABLE_CSV_FILENAMES["gold_fact_product_events_aggregated"]
        detail_count = con.execute("SELECT COUNT(*) FROM gold_fact_product_events").fetchone()[0]
        if agg_csv.is_file():
            total = 0
            with agg_csv.open(newline="", encoding="utf-8") as handle:
                reader = csv.DictReader(handle)
                for row in reader:
                    total += int(row["EventCount"])
            if total != detail_count:
                errors.append(
                    f"Aggregated EventCount sum {total} != detail {detail_count}"
                )
    finally:
        con.close()

    if partial and not errors:
        errors.append("Export set is partial relative to full GOLD_TABLE_CSV_FILENAMES")

    return ExportValidationResult(
        passed=not errors,
        partial=partial,
        errors=errors,
        files_validated=files,
    )
