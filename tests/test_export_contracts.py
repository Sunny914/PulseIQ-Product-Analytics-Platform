"""
WS-9 Gold CSV export contracts (temp DuckDB + temp export dir).
"""

from __future__ import annotations

import csv
import os
import subprocess
import sys
from pathlib import Path

import duckdb
import pytest

from pipeline_helpers import REPO_ROOT, run_full_dq_pipeline

sys.path.insert(0, str(REPO_ROOT / "sql"))
from gold_table_schemas import (  # noqa: E402
    GOLD_FACT_ACTIVATION_AS_OF_COLUMNS,
    GOLD_FACT_PRODUCT_EVENTS_AGGREGATED_COLUMNS,
    GOLD_FACT_PRODUCT_EVENTS_DETAIL_COLUMNS,
    GOLD_TABLE_CSV_FILENAMES,
)

SQL = REPO_ROOT / "sql"
EXPORT_SCRIPT = SQL / "gold" / "export_gold_to_csv.py"

SCHEMA_BY_TABLE = {
    "gold_fact_product_events": GOLD_FACT_PRODUCT_EVENTS_DETAIL_COLUMNS,
    "gold_fact_product_events_aggregated": GOLD_FACT_PRODUCT_EVENTS_AGGREGATED_COLUMNS,
    "gold_fact_activation_as_of": GOLD_FACT_ACTIVATION_AS_OF_COLUMNS,
}


@pytest.fixture
def export_fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    monkeypatch.setenv("PULSEIQ_AS_OF_DATE", "2026-07-11")
    db_path = tmp_path / "pulseiq_export.duckdb"
    export_dir = tmp_path / "gold_csv"
    monkeypatch.setenv("PULSEIQ_DB_PATH", str(db_path))
    run_full_dq_pipeline(db_path)
    return db_path, export_dir


def _run_export(
    db_path: Path,
    export_dir: Path,
    *,
    tables: str | None = None,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PULSEIQ_DB_PATH"] = str(db_path)
    env["PULSEIQ_EXPORT_DIR"] = str(export_dir)
    if tables is not None:
        env["PULSEIQ_EXPORT_TABLES"] = tables
    return subprocess.run(
        [sys.executable, str(EXPORT_SCRIPT)],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_full_export_all_mapped_tables(export_fixture: tuple[Path, Path]) -> None:
    db_path, export_dir = export_fixture
    proc = _run_export(db_path, export_dir)
    assert proc.returncode == 0, proc.stderr or proc.stdout

    con = duckdb.connect(str(db_path), read_only=True)
    try:
        for table, csv_name in GOLD_TABLE_CSV_FILENAMES.items():
            csv_path = export_dir / csv_name
            assert csv_path.is_file(), f"missing export for {table}"
            with csv_path.open(newline="", encoding="utf-8") as handle:
                header = next(csv.reader(handle))
            db_cols = [row[0] for row in con.execute(f'DESCRIBE "{table}"').fetchall()]
            assert header == db_cols, table

            if table in SCHEMA_BY_TABLE:
                assert header == list(SCHEMA_BY_TABLE[table])

            db_rows = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            with csv_path.open(newline="", encoding="utf-8") as handle:
                row_count = sum(1 for _ in csv.reader(handle)) - 1
            assert row_count == db_rows, table
    finally:
        con.close()


def test_activation_as_of_ttv_columns_in_export(export_fixture: tuple[Path, Path]) -> None:
    db_path, export_dir = export_fixture
    _run_export(db_path, export_dir)
    csv_path = export_dir / "fact_activation_as_of.csv"
    with csv_path.open(newline="", encoding="utf-8") as handle:
        header = next(csv.reader(handle))
    assert "TimeToValueDaysFullDataset" in header
    assert "TimeToValueDaysAsOf" in header


def test_aggregated_export_event_count_reconciles(export_fixture: tuple[Path, Path]) -> None:
    db_path, export_dir = export_fixture
    _run_export(db_path, export_dir)
    csv_path = export_dir / "fact_product_events_aggregated.csv"
    total = 0
    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            total += int(row["EventCount"])
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        assert total == con.execute(
            "SELECT COUNT(*) FROM gold_fact_product_events"
        ).fetchone()[0]
    finally:
        con.close()


def test_partial_export_skips_missing_by_design(export_fixture: tuple[Path, Path]) -> None:
    """Subset export is intentionally partial; only requested files must exist."""
    db_path, export_dir = export_fixture
    subset = "gold_fact_product_events,gold_fact_activation_as_of"
    proc = _run_export(db_path, export_dir, tables=subset)
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert (export_dir / "fact_product_events.csv").is_file()
    assert (export_dir / "fact_activation_as_of.csv").is_file()
    assert not (export_dir / "fact_deals.csv").is_file()


def test_export_idempotent_headers(export_fixture: tuple[Path, Path]) -> None:
    db_path, export_dir = export_fixture
    _run_export(db_path, export_dir)
    first = (export_dir / "fact_product_events.csv").read_text(encoding="utf-8").splitlines()[0]
    _run_export(db_path, export_dir)
    second = (export_dir / "fact_product_events.csv").read_text(encoding="utf-8").splitlines()[0]
    assert first == second
