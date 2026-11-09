"""
WS-8.1 supplementary activation-as-of tests (temporary DuckDB only).
"""

from __future__ import annotations

import sys
from pathlib import Path

import duckdb
import pytest

from pipeline_helpers import REPO_ROOT, run_lifecycle_pipeline, run_script

sys.path.insert(0, str(REPO_ROOT / "sql"))
from gold_table_schemas import GOLD_FACT_ACTIVATION_AS_OF_COLUMNS  # noqa: E402

SQL = REPO_ROOT / "sql"


@pytest.fixture
def activation_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("PULSEIQ_AS_OF_DATE", "2026-07-11")
    db_path = tmp_path / "pulseiq_ws81.duckdb"
    monkeypatch.setenv("PULSEIQ_DB_PATH", str(db_path))
    run_lifecycle_pipeline(db_path)
    return db_path


def test_schema_contract(activation_db: Path) -> None:
    con = duckdb.connect(str(activation_db), read_only=True)
    try:
        cols = [
            row[0]
            for row in con.execute("DESCRIBE gold_fact_activation_as_of").fetchall()
        ]
        assert cols == list(GOLD_FACT_ACTIVATION_AS_OF_COLUMNS)
    finally:
        con.close()


def test_one_row_per_account(activation_db: Path) -> None:
    con = duckdb.connect(str(activation_db), read_only=True)
    try:
        n = con.execute("SELECT COUNT(*) FROM gold_fact_activation_as_of").fetchone()[0]
        distinct = con.execute(
            "SELECT COUNT(DISTINCT AccountId) FROM gold_fact_activation_as_of"
        ).fetchone()[0]
        dim_n = con.execute("SELECT COUNT(*) FROM gold_dim_accounts").fetchone()[0]
        assert n == 120 == distinct == dim_n
    finally:
        con.close()


def test_full_dataset_baseline(activation_db: Path) -> None:
    con = duckdb.connect(str(activation_db), read_only=True)
    try:
        row = con.execute(
            """
            SELECT
                COUNT(*),
                SUM(CASE WHEN IsActivatedFullDataset THEN 1 ELSE 0 END),
                AVG(TimeToValueDaysFullDataset) FILTER (WHERE IsActivatedFullDataset),
                approx_quantile(TimeToValueDaysFullDataset, 0.5)
                    FILTER (WHERE IsActivatedFullDataset)
            FROM gold_fact_activation_as_of
            """
        ).fetchone()
        assert row[0] == 120
        assert row[1] == 21
        assert abs(float(row[2]) - 9.904761904761905) < 1e-6
        assert row[3] == 10

        legacy = con.execute(
            """
            SELECT COUNT(*), SUM(CASE WHEN IsActivated THEN 1 ELSE 0 END),
                   AVG(TimeToValueDays) FILTER (WHERE IsActivated)
            FROM gold_fact_advanced_activation
            """
        ).fetchone()
        assert legacy == (120, 21, row[2])
    finally:
        con.close()


def test_cohort_maturity_and_eligibility(activation_db: Path) -> None:
    con = duckdb.connect(str(activation_db), read_only=True)
    try:
        assert con.execute(
            "SELECT ReportAsOfDate FROM gold_fact_activation_as_of LIMIT 1"
        ).fetchone()[0].isoformat() == "2026-07-11"

        cohort = con.execute(
            """
            SELECT
                COUNT(*) FILTER (WHERE CAST(CreatedDate AS DATE) <= ReportAsOfDate),
                COUNT(*) FILTER (WHERE IsEligibleAsOf),
                COUNT(*) FILTER (
                    WHERE CAST(CreatedDate AS DATE) <= ReportAsOfDate
                      AND NOT IsEligibleAsOf
                ),
                COUNT(*) FILTER (WHERE IsFutureCreated),
                COUNT(*) FILTER (WHERE IsActivatedAsOf),
                COUNT(*) FILTER (WHERE IsEligibleAsOf AND IsActivatedAsOf)
            FROM gold_fact_activation_as_of
            """
        ).fetchone()
        assert cohort == (16, 15, 1, 104, 0, 0)

        assert con.execute(
            """
            SELECT COUNT(*) FROM gold_fact_activation_as_of
            WHERE IsEligibleAsOf AND NOT IsActivatedAsOf
            """
        ).fetchone()[0] == 15
    finally:
        con.close()


def test_ineligible_not_counted_as_unactivated_in_as_of_rate(activation_db: Path) -> None:
    con = duckdb.connect(str(activation_db), read_only=True)
    try:
        eligible = con.execute(
            "SELECT COUNT(*) FROM gold_fact_activation_as_of WHERE IsEligibleAsOf"
        ).fetchone()[0]
        activated_as_of = con.execute(
            """
            SELECT COUNT(*) FROM gold_fact_activation_as_of
            WHERE IsEligibleAsOf AND IsActivatedAsOf
            """
        ).fetchone()[0]
        assert eligible == 15
        assert activated_as_of == 0
        assert activated_as_of / eligible == 0.0

        full_activated = con.execute(
            """
            SELECT COUNT(*) FROM gold_fact_activation_as_of
            WHERE IsActivatedFullDataset
            """
        ).fetchone()[0]
        assert full_activated == 21
    finally:
        con.close()


def test_future_and_incomplete_window_flags(activation_db: Path) -> None:
    con = duckdb.connect(str(activation_db), read_only=True)
    try:
        assert con.execute(
            """
            SELECT COUNT(*) FROM gold_fact_activation_as_of
            WHERE IsFutureCreated AND IsEligibleAsOf
            """
        ).fetchone()[0] == 0

        incomplete = con.execute(
            """
            SELECT COUNT(*) FROM gold_fact_activation_as_of
            WHERE NOT IsWindowCompleteAsOf AND IsFutureCreated
            """
        ).fetchone()[0]
        assert incomplete == 104

        assert con.execute(
            """
            SELECT COUNT(*) FROM gold_fact_activation_as_of
            WHERE IsWindowCompleteAsOf AND NOT IsEligibleAsOf
            """
        ).fetchone()[0] == 0
    finally:
        con.close()


def test_ttv_null_for_unactivated(activation_db: Path) -> None:
    con = duckdb.connect(str(activation_db), read_only=True)
    try:
        assert con.execute(
            """
            SELECT COUNT(*) FROM gold_fact_activation_as_of
            WHERE NOT IsActivatedFullDataset AND TimeToValueDaysFullDataset IS NOT NULL
            """
        ).fetchone()[0] == 0
        assert con.execute(
            """
            SELECT COUNT(*) FROM gold_fact_activation_as_of
            WHERE IsActivatedFullDataset AND TimeToValueDaysFullDataset IS NULL
            """
        ).fetchone()[0] == 0
    finally:
        con.close()


def test_ttv_full_dataset_matches_advanced_activation(activation_db: Path) -> None:
    con = duckdb.connect(str(activation_db), read_only=True)
    try:
        mismatch = con.execute(
            """
            SELECT COUNT(*)
            FROM gold_fact_activation_as_of f
            INNER JOIN gold_fact_advanced_activation a
                ON f.AccountId = a.AccountId
            WHERE f.TimeToValueDaysFullDataset IS DISTINCT FROM a.TimeToValueDays
            """
        ).fetchone()[0]
        assert mismatch == 0
    finally:
        con.close()


def test_ttv_as_of_semantics(activation_db: Path) -> None:
    con = duckdb.connect(str(activation_db), read_only=True)
    try:
        assert con.execute(
            """
            SELECT COUNT(*) FROM gold_fact_activation_as_of
            WHERE NOT IsEligibleAsOf AND TimeToValueDaysAsOf IS NOT NULL
            """
        ).fetchone()[0] == 0

        assert con.execute(
            """
            SELECT COUNT(*) FROM gold_fact_activation_as_of
            WHERE IsFutureCreated AND TimeToValueDaysAsOf IS NOT NULL
            """
        ).fetchone()[0] == 0

        assert con.execute(
            """
            SELECT COUNT(*) FROM gold_fact_activation_as_of
            WHERE IsEligibleAsOf AND NOT IsActivatedAsOf
              AND TimeToValueDaysAsOf IS NOT NULL
            """
        ).fetchone()[0] == 0

        assert con.execute(
            """
            SELECT COUNT(*) FROM gold_fact_activation_as_of
            WHERE IsActivatedFullDataset AND NOT IsEligibleAsOf
              AND TimeToValueDaysAsOf IS NOT NULL
            """
        ).fetchone()[0] == 0

        assert con.execute(
            """
            SELECT COUNT(*) FROM gold_fact_activation_as_of
            WHERE (IsEligibleAsOf AND IsActivatedAsOf)
              IS DISTINCT FROM (TimeToValueDaysAsOf IS NOT NULL)
            """
        ).fetchone()[0] == 0

        assert con.execute(
            """
            SELECT COUNT(*) FROM gold_fact_activation_as_of
            WHERE IsEligibleAsOf AND IsActivatedAsOf
              AND TimeToValueDaysAsOf IS DISTINCT FROM TimeToValueDaysFullDataset
            """
        ).fetchone()[0] == 0

        assert con.execute(
            "SELECT COUNT(*) FROM gold_fact_activation_as_of WHERE TimeToValueDaysAsOf IS NOT NULL"
        ).fetchone()[0] == 0
    finally:
        con.close()


def test_segment_eligible_denominators(activation_db: Path) -> None:
    con = duckdb.connect(str(activation_db), read_only=True)
    try:
        rows = con.execute(
            """
            SELECT a.Segment,
                COUNT(*) FILTER (WHERE f.IsEligibleAsOf) AS eligible,
                COUNT(*) FILTER (WHERE f.IsEligibleAsOf AND f.IsActivatedAsOf) AS activated
            FROM gold_fact_activation_as_of f
            JOIN gold_dim_accounts a ON f.AccountId = a.AccountId
            GROUP BY 1
            ORDER BY eligible DESC
            """
        ).fetchall()
        assert rows[0][0] == "SMB" and rows[0][1] == 13 and rows[0][2] == 0
        assert sum(r[1] for r in rows) == 15
    finally:
        con.close()


def test_advanced_activation_unchanged_after_as_of_build(
    activation_db: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    con = duckdb.connect(str(activation_db), read_only=True)
    before = con.execute(
        """
        SELECT AccountId, IsActivated, TimeToValueDays
        FROM gold_fact_advanced_activation ORDER BY AccountId
        """
    ).fetchall()
    con.close()

    monkeypatch.setenv("PULSEIQ_DB_PATH", str(activation_db))
    monkeypatch.setenv("PULSEIQ_AS_OF_DATE", "2026-07-11")
    run_script(SQL / "gold" / "gold_fact_advanced_activation.py", activation_db)
    run_script(SQL / "gold" / "gold_fact_activation_as_of.py", activation_db)

    con = duckdb.connect(str(activation_db), read_only=True)
    after = con.execute(
        """
        SELECT AccountId, IsActivated, TimeToValueDays
        FROM gold_fact_advanced_activation ORDER BY AccountId
        """
    ).fetchall()
    con.close()
    assert before == after


def test_deterministic_rerun(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PULSEIQ_AS_OF_DATE", "2026-07-11")
    db_path = tmp_path / "ws81_det.duckdb"
    monkeypatch.setenv("PULSEIQ_DB_PATH", str(db_path))
    run_lifecycle_pipeline(db_path)
    con = duckdb.connect(str(db_path), read_only=True)
    first = con.execute(
        "SELECT * FROM gold_fact_activation_as_of ORDER BY AccountId"
    ).fetchall()
    con.close()

    run_script(SQL / "gold" / "gold_fact_activation_as_of.py", db_path)
    con = duckdb.connect(str(db_path), read_only=True)
    second = con.execute(
        "SELECT * FROM gold_fact_activation_as_of ORDER BY AccountId"
    ).fetchall()
    con.close()
    assert first == second
