"""
WS-4.1: Aggregated Gold schema validation, reconciliation, and CSV export (temp DB only).
"""

from __future__ import annotations

import csv
import os
import subprocess
import sys
from pathlib import Path

import duckdb
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SQL = REPO_ROOT / "sql"
sys.path.insert(0, str(SQL))

from gold_table_schemas import (  # noqa: E402
    GOLD_FACT_PRODUCT_EVENTS_AGGREGATED_COLUMNS,
    GOLD_FACT_PRODUCT_EVENTS_DETAIL_COLUMNS,
)

GOLD_EVENT_SCRIPTS = [
    SQL / "gold" / "gold_fact_product_events.py",
    SQL / "gold" / "gold_fact_product_events_aggregated.py",
]


def _run(script: Path, db_path: Path, *, extra_args: list[str] | None = None) -> None:
    env = os.environ.copy()
    env["PULSEIQ_DB_PATH"] = str(db_path)
    cmd = [sys.executable, str(script)]
    if extra_args:
        cmd.extend(extra_args)
    proc = subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


@pytest.fixture
def gold_event_db(tmp_path: Path) -> Path:
    from pipeline_helpers import run_minimal_event_pipeline

    db_path = tmp_path / "pulseiq_ws41.duckdb"
    run_minimal_event_pipeline(db_path)
    for script in GOLD_EVENT_SCRIPTS:
        _run(script, db_path)
    return db_path


def test_aggregated_schema_columns(gold_event_db: Path) -> None:
    con = duckdb.connect(str(gold_event_db), read_only=True)
    try:
        cols = [
            row[0]
            for row in con.execute("DESCRIBE gold_fact_product_events_aggregated").fetchall()
        ]
        assert cols == list(GOLD_FACT_PRODUCT_EVENTS_AGGREGATED_COLUMNS)
    finally:
        con.close()


def test_detail_schema_includes_original_and_normalized_names(gold_event_db: Path) -> None:
    con = duckdb.connect(str(gold_event_db), read_only=True)
    try:
        cols = [
            row[0]
            for row in con.execute("DESCRIBE gold_fact_product_events").fetchall()
        ]
        assert cols == list(GOLD_FACT_PRODUCT_EVENTS_DETAIL_COLUMNS)
        assert "EventName" in cols and "EventNameNormalized" in cols
    finally:
        con.close()


def test_event_count_reconciliation(gold_event_db: Path) -> None:
    con = duckdb.connect(str(gold_event_db), read_only=True)
    try:
        detail_n = con.execute("SELECT COUNT(*) FROM gold_fact_product_events").fetchone()[0]
        agg_sum = con.execute(
            "SELECT COALESCE(SUM(EventCount), 0) FROM gold_fact_product_events_aggregated"
        ).fetchone()[0]
        assert detail_n == 60552
        assert agg_sum == detail_n
    finally:
        con.close()


def test_csv_export_aggregated_schema(gold_event_db: Path, tmp_path: Path) -> None:
    export_dir = tmp_path / "gold_csv"
    export_dir.mkdir()
    env = os.environ.copy()
    env["PULSEIQ_DB_PATH"] = str(gold_event_db)
    env["PULSEIQ_EXPORT_DIR"] = str(export_dir)
    env["PULSEIQ_EXPORT_TABLES"] = (
        "gold_fact_product_events,gold_fact_product_events_aggregated"
    )
    proc = subprocess.run(
        [sys.executable, str(SQL / "gold" / "export_gold_to_csv.py")],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout

    csv_path = export_dir / "fact_product_events_aggregated.csv"
    assert csv_path.is_file(), proc.stdout

    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        header = next(reader)
    assert header == list(GOLD_FACT_PRODUCT_EVENTS_AGGREGATED_COLUMNS)
