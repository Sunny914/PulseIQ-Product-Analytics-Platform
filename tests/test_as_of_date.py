"""
WS-7 as_of_date, tenure, recency, and activation regression tests (temp DB only).
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import duckdb
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SQL = REPO_ROOT / "sql"

sys.path.insert(0, str(SQL))
from db_config import DEFAULT_AS_OF_DATE, get_as_of_date  # noqa: E402

from pipeline_helpers import run_lifecycle_pipeline, run_script  # noqa: E402


class TestAsOfDateConfig:
    def test_default_date(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("PULSEIQ_AS_OF_DATE", raising=False)
        assert get_as_of_date() == date(2026, 7, 11)
        assert get_as_of_date() == DEFAULT_AS_OF_DATE

    def test_valid_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PULSEIQ_AS_OF_DATE", "2026-11-06")
        assert get_as_of_date() == date(2026, 11, 6)

    def test_invalid_format_rejected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PULSEIQ_AS_OF_DATE", "07/11/2026")
        with pytest.raises(ValueError, match="ISO YYYY-MM-DD"):
            get_as_of_date()

    def test_invalid_calendar_date_rejected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PULSEIQ_AS_OF_DATE", "2026-02-30")
        with pytest.raises(ValueError, match="not a valid calendar date"):
            get_as_of_date()


def _run_lifecycle(tmp_path: Path, as_of: str, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / f"pulseiq_ws7_{as_of.replace('-', '')}.duckdb"
    monkeypatch.setenv("PULSEIQ_AS_OF_DATE", as_of)
    monkeypatch.setenv("PULSEIQ_DB_PATH", str(db_path))
    run_lifecycle_pipeline(db_path)
    return db_path


@pytest.fixture
def lifecycle_july(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    return _run_lifecycle(tmp_path, "2026-07-11", monkeypatch)


def test_account_age_future_and_normal(lifecycle_july: Path) -> None:
    con = duckdb.connect(str(lifecycle_july), read_only=True)
    try:
        future = con.execute(
            "SELECT COUNT(*) FROM silver_accounts WHERE is_future_created"
        ).fetchone()[0]
        assert future == 104
        assert con.execute(
            """
            SELECT COUNT(*) FROM silver_accounts
            WHERE is_future_created AND account_age_days IS NULL
              AND account_age_bucket = 'future'
            """
        ).fetchone()[0] == future

        sample = con.execute(
            """
            SELECT account_age_days FROM silver_accounts
            WHERE NOT is_future_created AND account_age_days IS NOT NULL
            LIMIT 1
            """
        ).fetchone()
        assert sample is not None
    finally:
        con.close()


def test_user_and_account_tenure_separate(lifecycle_july: Path) -> None:
    con = duckdb.connect(str(lifecycle_july), read_only=True)
    try:
        mismatch_acct = con.execute(
            """
            SELECT COUNT(*) FROM silver_users u
            INNER JOIN silver_accounts a ON u.account_id = a.account_id
            WHERE u.account_tenure_days IS DISTINCT FROM a.account_age_days
            """
        ).fetchone()[0]
        assert mismatch_acct == 0

        distinct_tenures = con.execute(
            """
            SELECT COUNT(*) FROM silver_users
            WHERE user_tenure_days IS NOT NULL
              AND account_tenure_days IS NOT NULL
              AND user_tenure_days IS DISTINCT FROM account_tenure_days
            """
        ).fetchone()[0]
        assert distinct_tenures >= 8

        assert con.execute(
            """
            SELECT COUNT(*) FROM silver_users
            WHERE is_future_created AND user_tenure_days IS NOT NULL
            """
        ).fetchone()[0] == 0
        assert con.execute("SELECT COUNT(*) FROM silver_users WHERE is_future_created").fetchone()[0] > 0
    finally:
        con.close()


def test_deal_age_open_only(lifecycle_july: Path) -> None:
    con = duckdb.connect(str(lifecycle_july), read_only=True)
    try:
        closed_with_age = con.execute(
            """
            SELECT COUNT(*) FROM silver_deals
            WHERE is_closed AND deal_age_days IS NOT NULL
            """
        ).fetchone()[0]
        assert closed_with_age == 0

        open_with_age = con.execute(
            """
            SELECT COUNT(*) FROM silver_deals
            WHERE NOT is_closed AND NOT is_future_created AND deal_age_days IS NOT NULL
            """
        ).fetchone()[0]
        assert open_with_age > 0

        assert con.execute(
            "SELECT COUNT(*) FROM silver_deals WHERE deal_cycle_days < 0"
        ).fetchone()[0] == 0
    finally:
        con.close()


def test_recency_future_last_seen(lifecycle_july: Path) -> None:
    con = duckdb.connect(str(lifecycle_july), read_only=True)
    try:
        future_seen = con.execute(
            """
            SELECT COUNT(*) FROM silver_users
            WHERE recency_bucket = 'future_last_seen'
              AND days_since_last_seen IS NULL
            """
        ).fetchone()[0]
        assert future_seen > 0

        bad_active = con.execute(
            """
            SELECT COUNT(*) FROM silver_users
            WHERE days_since_last_seen < 0
              AND recency_bucket IN ('<7 days', '7-29 days', '30-89 days', '90+ days')
            """
        ).fetchone()[0]
        assert bad_active == 0

        null_seen = con.execute(
            """
            SELECT COUNT(*) FROM silver_users
            WHERE last_seen_at IS NULL AND recency_bucket IS NULL
            """
        ).fetchone()[0]
        assert null_seen == 15
    finally:
        con.close()


def test_recency_bucket_boundaries_sql() -> None:
    """Logic unit test for bucket edges at a fixed as_of."""
    con = duckdb.connect()
    try:
        rows = con.execute(
            """
            WITH cases AS (
                SELECT * FROM (VALUES
                    (DATE '2026-07-05', '<7 days'),
                    (DATE '2026-07-04', '7-29 days'),
                    (DATE '2026-06-12', '7-29 days'),
                    (DATE '2026-06-11', '30-89 days'),
                    (DATE '2026-04-13', '30-89 days'),
                    (DATE '2026-04-12', '90+ days')
                ) AS t(last_seen_date, expected)
            ),
            bucketed AS (
                SELECT
                    last_seen_date,
                    expected,
                    CASE
                        WHEN last_seen_date > DATE '2026-07-11' THEN 'future_last_seen'
                        WHEN DATE_DIFF('day', last_seen_date, DATE '2026-07-11') < 7
                            THEN '<7 days'
                        WHEN DATE_DIFF('day', last_seen_date, DATE '2026-07-11') < 30
                            THEN '7-29 days'
                        WHEN DATE_DIFF('day', last_seen_date, DATE '2026-07-11') < 90
                            THEN '30-89 days'
                        ELSE '90+ days'
                    END AS bucket
                FROM cases
            )
            SELECT COUNT(*) FROM bucketed WHERE bucket <> expected
            """
        ).fetchone()[0]
        assert rows == 0
    finally:
        con.close()


def test_activation_regression_unchanged_across_as_of(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    july = _run_lifecycle(tmp_path, "2026-07-11", monkeypatch)
    nov = _run_lifecycle(tmp_path, "2026-11-06", monkeypatch)

    for db_path in (july, nov):
        con = duckdb.connect(str(db_path), read_only=True)
        try:
            activated, avg_ttv = con.execute(
                """
                SELECT
                    SUM(CASE WHEN IsActivated THEN 1 ELSE 0 END),
                    AVG(TimeToValueDays) FILTER (WHERE IsActivated)
                FROM gold_fact_advanced_activation
                """
            ).fetchone()
            assert activated == 21
            assert avg_ttv is not None
            assert abs(float(avg_ttv) - 9.904761904761905) < 1e-6
        finally:
            con.close()


def test_date_metrics_change_when_as_of_changes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    july = _run_lifecycle(tmp_path, "2026-07-11", monkeypatch)
    nov = _run_lifecycle(tmp_path, "2026-11-06", monkeypatch)

    con_j = duckdb.connect(str(july), read_only=True)
    con_n = duckdb.connect(str(nov), read_only=True)
    try:
        avg_j = con_j.execute(
            "SELECT AVG(account_age_days) FROM silver_accounts WHERE account_age_days IS NOT NULL"
        ).fetchone()[0]
        avg_n = con_n.execute(
            "SELECT AVG(account_age_days) FROM silver_accounts WHERE account_age_days IS NOT NULL"
        ).fetchone()[0]
        assert avg_n > avg_j
    finally:
        con_j.close()
        con_n.close()


def test_deterministic_rerun(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db_path = tmp_path / "ws7_det.duckdb"
    monkeypatch.setenv("PULSEIQ_AS_OF_DATE", "2026-07-11")
    monkeypatch.setenv("PULSEIQ_DB_PATH", str(db_path))

    for _ in range(2):
        run_lifecycle_pipeline(db_path)

    con = duckdb.connect(str(db_path), read_only=True)
    try:
        rows = con.execute(
            """
            SELECT user_id, user_tenure_days, account_tenure_days, recency_bucket
            FROM silver_users ORDER BY user_id
            """
        ).fetchall()
        assert len(rows) == 400
    finally:
        con.close()


def test_gold_exposes_account_tenure(lifecycle_july: Path) -> None:
    con = duckdb.connect(str(lifecycle_july), read_only=True)
    try:
        cols = {r[0] for r in con.execute("DESCRIBE gold_dim_users").fetchall()}
        assert "AccountTenureDays" in cols
        assert "IsFutureCreated" in cols
    finally:
        con.close()
