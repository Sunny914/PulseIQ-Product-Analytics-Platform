"""
WS-12 product analytics Gold models — disposable DuckDB only.
"""

from __future__ import annotations

import sys
from pathlib import Path

import duckdb
import pytest

from pipeline_helpers import REPO_ROOT, run_full_dq_pipeline

SQL = REPO_ROOT / "sql"
sys.path.insert(0, str(SQL))
from product_analytics_sql import VALID_PRODUCT_FEATURES  # noqa: E402


@pytest.fixture
def analytics_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("PULSEIQ_AS_OF_DATE", "2026-07-11")
    db_path = tmp_path / "ws12.duckdb"
    monkeypatch.setenv("PULSEIQ_DB_PATH", str(db_path))
    run_full_dq_pipeline(db_path)
    return db_path


def test_attribution_counts_unchanged(analytics_db: Path) -> None:
    con = duckdb.connect(str(analytics_db), read_only=True)
    try:
        rows = dict(
            con.execute(
                "SELECT account_resolution_status, COUNT(*) FROM silver_product_events GROUP BY 1"
            ).fetchall()
        )
        assert rows == {"SOURCE_VERIFIED": 59911, "ENRICHED": 226, "QUARANTINED": 415}
    finally:
        con.close()


def test_activation_regression(analytics_db: Path) -> None:
    con = duckdb.connect(str(analytics_db), read_only=True)
    try:
        act = con.execute(
            """
            SELECT SUM(CASE WHEN IsActivated THEN 1 ELSE 0 END), COUNT(*),
                   AVG(TimeToValueDays) FILTER (WHERE IsActivated)
            FROM gold_fact_advanced_activation
            """
        ).fetchone()
        assert act[0] == 21 and act[1] == 120
        assert abs(float(act[2]) - 9.904761904761905) < 1e-5
        asof = con.execute(
            """
            SELECT SUM(CASE WHEN IsEligibleAsOf THEN 1 ELSE 0 END),
                   SUM(CASE WHEN IsEligibleAsOf AND IsActivatedAsOf THEN 1 ELSE 0 END)
            FROM gold_fact_activation_as_of
            """
        ).fetchone()
        assert asof == (15, 0)
    finally:
        con.close()


def test_engagement_daily_reconciles(analytics_db: Path) -> None:
    con = duckdb.connect(str(analytics_db), read_only=True)
    try:
        ref_date = "2026-04-01"
        ref = con.execute(
            f"""
            SELECT COUNT(DISTINCT UserId) FROM gold_fact_qualified_product_events
            WHERE IsOfficialUserQualified AND EventDate = DATE '{ref_date}'
            """
        ).fetchone()[0]
        model = con.execute(
            f"""
            SELECT ActiveEntityCount FROM gold_fact_engagement_periodic
            WHERE ReportContext = 'FULL_DATASET' AND PeriodType = 'DAY'
              AND PeriodStartDate = DATE '{ref_date}'
              AND EntityType = 'USER' AND AttributionPopulation = 'OFFICIAL'
            """
        ).fetchone()[0]
        assert model == ref
        asof = con.execute(
            f"""
            SELECT ActiveEntityCount FROM gold_fact_engagement_periodic
            WHERE ReportContext = 'AS_OF' AND PeriodType = 'DAY'
              AND PeriodStartDate = DATE '{ref_date}'
              AND EntityType = 'USER' AND AttributionPopulation = 'OFFICIAL'
            """
        ).fetchone()[0]
        assert asof == ref
    finally:
        con.close()


def test_engagement_as_of_excludes_future_events(analytics_db: Path) -> None:
    con = duckdb.connect(str(analytics_db), read_only=True)
    try:
        future = con.execute(
            """
            SELECT COUNT(DISTINCT UserId) FROM gold_fact_product_events
            WHERE AccountResolutionStatus = 'SOURCE_VERIFIED' AND UserId IS NOT NULL
              AND EventDate > DATE '2026-07-11'
            """
        ).fetchone()[0]
        assert future > 0
        full = con.execute(
            """
            SELECT SUM(ActiveEntityCount) FROM gold_fact_engagement_periodic
            WHERE ReportContext = 'FULL_DATASET' AND PeriodType = 'DAY'
              AND EntityType = 'USER' AND AttributionPopulation = 'OFFICIAL'
              AND PeriodStartDate > DATE '2026-07-11'
            """
        ).fetchone()[0]
        asof = con.execute(
            """
            SELECT COALESCE(SUM(ActiveEntityCount), 0) FROM gold_fact_engagement_periodic
            WHERE ReportContext = 'AS_OF' AND PeriodType = 'DAY'
              AND EntityType = 'USER' AND AttributionPopulation = 'OFFICIAL'
              AND PeriodStartDate > DATE '2026-07-11'
            """
        ).fetchone()[0]
        assert full > 0 and asof == 0
    finally:
        con.close()


def test_engagement_active_count_never_exceeds_cap(analytics_db: Path) -> None:
    con = duckdb.connect(str(analytics_db), read_only=True)
    try:
        bad = con.execute(
            """
            SELECT COUNT(*) FROM gold_fact_engagement_periodic
            WHERE ActiveEntityCount > EligibleEntityPopulationCap
            """
        ).fetchone()[0]
        assert bad == 0
    finally:
        con.close()


def test_feature_adoption_distinct_reconcile(analytics_db: Path) -> None:
    con = duckdb.connect(str(analytics_db), read_only=True)
    try:
        for feat in VALID_PRODUCT_FEATURES:
            ref = con.execute(
                f"""
                SELECT COUNT(DISTINCT AccountId) FROM gold_fact_qualified_product_events
                WHERE IsOfficialAccountQualified AND FeatureName = '{feat}'
                """
            ).fetchone()[0]
            model = con.execute(
                f"""
                SELECT COUNT(*) FROM gold_fact_feature_adoption_account
                WHERE ReportContext = 'FULL_DATASET' AND AttributionPopulation = 'OFFICIAL'
                  AND FeatureName = '{feat}'
                """
            ).fetchone()[0]
            assert model == ref
    finally:
        con.close()


def test_feature_breadth_max_four(analytics_db: Path) -> None:
    con = duckdb.connect(str(analytics_db), read_only=True)
    try:
        mx = con.execute(
            "SELECT MAX(DistinctFeatureCount) FROM gold_fact_feature_breadth_user"
        ).fetchone()[0]
        assert mx <= 4
        assert con.execute(
            "SELECT COUNT(*) FROM gold_fact_feature_breadth_user WHERE UserId IS NULL"
        ).fetchone()[0] == 0
    finally:
        con.close()


def test_recency_no_negative_days(analytics_db: Path) -> None:
    con = duckdb.connect(str(analytics_db), read_only=True)
    try:
        neg = con.execute(
            """
            SELECT COUNT(*) FROM gold_fact_product_activity_recency_user
            WHERE ReportContext = 'AS_OF' AND DaysSinceLastActivity < 0
            """
        ).fetchone()[0]
        assert neg == 0
        future_leak = con.execute(
            """
            SELECT COUNT(*) FROM gold_fact_product_activity_recency_user
            WHERE ReportContext = 'AS_OF' AND LastActivityDate > ReportAsOfDate
            """
        ).fetchone()[0]
        assert future_leak == 0
    finally:
        con.close()


def test_monthly_adoption_not_sum_of_daily(analytics_db: Path) -> None:
    """Monthly distinct must come from period table, not summing daily engagement."""
    con = duckdb.connect(str(analytics_db), read_only=True)
    try:
        month_start = con.execute(
            """
            SELECT MIN(PeriodStartDate) FROM gold_fact_feature_adoption_by_period
            WHERE EntityType = 'USER' AND ReportContext = 'AS_OF'
            """
        ).fetchone()[0]
        daily_sum = con.execute(
            """
            SELECT COALESCE(SUM(ActiveEntityCount), 0)
            FROM gold_fact_engagement_periodic
            WHERE ReportContext = 'AS_OF' AND PeriodType = 'DAY'
              AND EntityType = 'USER' AND AttributionPopulation = 'OFFICIAL'
              AND PeriodStartDate >= ? AND PeriodStartDate <= ? + INTERVAL 1 MONTH
            """,
            [month_start, month_start],
        ).fetchone()[0]
        monthly = con.execute(
            """
            SELECT MAX(AdoptedEntityCount)
            FROM gold_fact_feature_adoption_by_period
            WHERE EntityType = 'USER' AND ReportContext = 'AS_OF'
              AND PeriodStartDate = ?
            """,
            [month_start],
        ).fetchone()[0]
        assert monthly <= 400
        assert daily_sum >= monthly
    finally:
        con.close()


def test_ws12_tables_exportable(analytics_db: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    export_dir = tmp_path / "csv"
    monkeypatch.setenv("PULSEIQ_DB_PATH", str(analytics_db))
    monkeypatch.setenv("PULSEIQ_EXPORT_DIR", str(export_dir))
    import subprocess

    proc = subprocess.run(
        [sys.executable, str(SQL / "gold" / "export_gold_to_csv.py")],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    assert (export_dir / "fact_engagement_periodic.csv").is_file()
