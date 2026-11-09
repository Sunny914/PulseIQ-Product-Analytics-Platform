"""
WS-4 event name normalization tests (temporary DuckDB only).
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


def _run(script: Path, db_path: Path) -> None:
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


def _pipeline(db_path: Path) -> None:
    from pipeline_helpers import run_minimal_event_pipeline

    run_minimal_event_pipeline(db_path)
    _run(SQL / "gold" / "gold_fact_product_events.py", db_path)
    _run(SQL / "gold" / "gold_fact_product_events_aggregated.py", db_path)


@pytest.fixture
def norm_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "pulseiq_ws4.duckdb"
    _pipeline(db_path)
    return db_path


def test_original_names_preserved_and_normalized(norm_db: Path) -> None:
    con = duckdb.connect(str(norm_db), read_only=True)
    try:
        assert con.execute("SELECT COUNT(*) FROM silver_product_events").fetchone()[0] == 60552
        assert con.execute(
            "SELECT COUNT(*) FROM silver_product_events WHERE event_name_normalized IS NULL"
        ).fetchone()[0] == 0

        aliases = con.execute(
            """
            SELECT event_name, event_name_normalized, COUNT(*) n
            FROM silver_product_events
            WHERE event_name IN ('ViewDashboard','Login','user_login')
            GROUP BY 1, 2
            ORDER BY 1
            """
        ).fetchall()
        assert aliases == [
            ("Login", "login", 83),
            ("ViewDashboard", "view_dashboard", 118),
            ("user_login", "login", 59),
        ]

        canonical = con.execute(
            """
            SELECT DISTINCT event_name_normalized FROM silver_product_events ORDER BY 1
            """
        ).fetchall()
        assert [r[0] for r in canonical] == [
            "create_deal",
            "enable_automation",
            "invite_user",
            "log_activity",
            "login",
            "move_deal_stage",
            "view_dashboard",
        ]
    finally:
        con.close()


def test_category_correction_for_login_alias(norm_db: Path) -> None:
    con = duckdb.connect(str(norm_db), read_only=True)
    try:
        assert con.execute(
            """
            SELECT COUNT(*) FROM silver_product_events
            WHERE event_name = 'Login' AND event_category = 'AUTH'
            """
        ).fetchone()[0] == 83
    finally:
        con.close()


def test_event_sk_unchanged_properties(norm_db: Path) -> None:
    con = duckdb.connect(str(norm_db), read_only=True)
    try:
        assert con.execute(
            "SELECT COUNT(*) FROM silver_product_events WHERE event_sk IS NULL"
        ).fetchone()[0] == 0
        assert con.execute(
            "SELECT COUNT(DISTINCT event_sk) FROM silver_product_events"
        ).fetchone()[0] == 60552
    finally:
        con.close()


def test_aggregation_reconciles_to_detail(norm_db: Path) -> None:
    con = duckdb.connect(str(norm_db), read_only=True)
    try:
        detail_sum = con.execute(
            "SELECT COUNT(*) FROM gold_fact_product_events"
        ).fetchone()[0]
        agg_sum = con.execute(
            "SELECT COALESCE(SUM(EventCount), 0) FROM gold_fact_product_events_aggregated"
        ).fetchone()[0]
        assert detail_sum == 60552
        assert agg_sum == 60552

        agg_rows = con.execute(
            "SELECT COUNT(*) FROM gold_fact_product_events_aggregated"
        ).fetchone()[0]
        assert agg_rows == 49300  # WS-6 grain includes FeatureName (was 30,797 pre-WS-6)
        assert agg_rows > 0
    finally:
        con.close()


def test_deterministic_silver_rerun(tmp_path: Path) -> None:
    from pipeline_helpers import run_minimal_event_pipeline

    db_path = tmp_path / "pulseiq_ws4_det.duckdb"
    run_minimal_event_pipeline(db_path)
    con = duckdb.connect(str(db_path), read_only=True)
    first = con.execute(
        "SELECT event_sk, event_name_normalized FROM silver_product_events ORDER BY event_sk"
    ).fetchall()
    con.close()
    _run(SQL / "silver" / "silver_product_events.py", db_path)
    con = duckdb.connect(str(db_path), read_only=True)
    second = con.execute(
        "SELECT event_sk, event_name_normalized FROM silver_product_events ORDER BY event_sk"
    ).fetchall()
    con.close()
    assert first == second
