"""
WS-3 event_sk tests using a temporary DuckDB (never the authoritative dev database).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import duckdb
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SQL = REPO_ROOT / "sql"


def _run_script(script: Path, db_path: Path) -> None:
    env = os.environ.copy()
    env["PULSEIQ_DB_PATH"] = str(db_path)
    proc = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def _run_silver(db_path: Path) -> list[str]:
    env = os.environ.copy()
    env["PULSEIQ_DB_PATH"] = str(db_path)
    proc = subprocess.run(
        [sys.executable, str(SQL / "silver" / "silver_product_events.py")],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        rows = con.execute(
            "SELECT event_sk FROM silver_product_events ORDER BY event_sk"
        ).fetchall()
        return [r[0] for r in rows]
    finally:
        con.close()


@pytest.fixture
def temp_event_db(tmp_path: Path) -> Path:
    from pipeline_helpers import run_minimal_event_pipeline

    db_path = tmp_path / "pulseiq_event_identity.duckdb"
    run_minimal_event_pipeline(db_path)
    _run_script(SQL / "gold" / "gold_fact_product_events.py", db_path)
    return db_path


def test_event_sk_constraints(temp_event_db: Path) -> None:
    con = duckdb.connect(str(temp_event_db), read_only=True)
    try:
        silver_n = con.execute("SELECT COUNT(*) FROM silver_product_events").fetchone()[0]
        assert silver_n == 60552

        null_sk = con.execute(
            "SELECT COUNT(*) FROM silver_product_events WHERE event_sk IS NULL"
        ).fetchone()[0]
        assert null_sk == 0

        distinct_sk = con.execute(
            "SELECT COUNT(DISTINCT event_sk) FROM silver_product_events"
        ).fetchone()[0]
        assert distinct_sk == silver_n

        null_event_id = con.execute(
            "SELECT COUNT(*) FROM silver_product_events WHERE event_id IS NULL"
        ).fetchone()[0]
        assert null_event_id == 616

        gold_n = con.execute("SELECT COUNT(*) FROM gold_fact_product_events").fetchone()[0]
        assert gold_n == silver_n

        gold_null_id = con.execute(
            'SELECT COUNT(*) FROM gold_fact_product_events WHERE "EventId" IS NULL'
        ).fetchone()[0]
        assert gold_null_id == 616

        gold_null_sk = con.execute(
            'SELECT COUNT(*) FROM gold_fact_product_events WHERE "EventSk" IS NULL'
        ).fetchone()[0]
        assert gold_null_sk == 0

        src_keys = con.execute(
            """
            SELECT COUNT(*) FROM silver_product_events
            WHERE event_id IS NOT NULL AND event_sk = 'SRC-' || event_id
            """
        ).fetchone()[0]
        non_null_id = con.execute(
            "SELECT COUNT(*) FROM silver_product_events WHERE event_id IS NOT NULL"
        ).fetchone()[0]
        assert src_keys == non_null_id

        sur_keys = con.execute(
            """
            SELECT COUNT(*) FROM silver_product_events
            WHERE event_id IS NULL AND event_sk LIKE 'SYN-%'
            """
        ).fetchone()[0]
        assert sur_keys == 616

        collisions = con.execute(
            """
            SELECT COUNT(*) FROM (
                SELECT event_sk FROM silver_product_events GROUP BY 1 HAVING COUNT(*)>1
            ) d
            """
        ).fetchone()[0]
        assert collisions == 0
    finally:
        con.close()


def test_source_event_id_unchanged_vs_bronze(temp_event_db: Path) -> None:
    con = duckdb.connect(str(temp_event_db), read_only=True)
    try:
        mismatch = con.execute(
            """
            SELECT COUNT(*) FROM silver_product_events s
            JOIN bronze_product_events b
              ON s.event_id IS NOT DISTINCT FROM b.event_id
             AND s.event_name = b.event_name
             AND s.user_id IS NOT DISTINCT FROM b.user_id
             AND s.account_id IS NOT DISTINCT FROM b.account_id
             AND s.deal_id IS NOT DISTINCT FROM b.deal_id
             AND s.event_timestamp = b.event_timestamp
             AND s.event_properties IS NOT DISTINCT FROM b.event_properties
             AND s.source_system = b.source_system
             AND b.is_test_event = FALSE
            """
        ).fetchone()[0]
        assert mismatch == 60552
    finally:
        con.close()


def test_event_sk_deterministic_across_runs(tmp_path: Path) -> None:
    from pipeline_helpers import run_minimal_event_pipeline

    db_path = tmp_path / "pulseiq_determinism.duckdb"
    run_minimal_event_pipeline(db_path)
    first = _run_silver(db_path)
    second = _run_silver(db_path)
    assert first == second
    assert len(first) == 60552


def test_raw_row_count_unchanged(temp_event_db: Path) -> None:
    con = duckdb.connect(str(temp_event_db), read_only=True)
    try:
        assert con.execute("SELECT COUNT(*) FROM raw__product_events").fetchone()[0] == 61747
        assert con.execute("SELECT COUNT(*) FROM bronze_product_events").fetchone()[0] == 61747
    finally:
        con.close()
