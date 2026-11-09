"""WS-13 chronology, retention, funnel, and segment tests."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

from pipeline_helpers import run_full_dq_pipeline


@pytest.fixture
def ws13_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("PULSEIQ_AS_OF_DATE", "2026-07-11")
    db = tmp_path / "ws13.duckdb"
    monkeypatch.setenv("PULSEIQ_DB_PATH", str(db))
    run_full_dq_pipeline(db)
    return db


def test_chronology_pre_creation_quantified(ws13_db: Path) -> None:
    con = duckdb.connect(str(ws13_db), read_only=True)
    try:
        n = con.execute(
            """
            SELECT COUNT(*) FROM gold_fact_qualified_product_events
            WHERE AccountChronologyClass = 'PRE_CREATION_EVENT'
            """
        ).fetchone()[0]
        assert n == 31161
        excluded = con.execute(
            "SELECT COUNT(*) FROM gold_fact_qualified_product_events WHERE IsOfficialAccountQualified"
        ).fetchone()[0]
        assert excluded < 59911
    finally:
        con.close()


def test_asof_feature_adoption_not_all_future_accounts(ws13_db: Path) -> None:
    con = duckdb.connect(str(ws13_db), read_only=True)
    try:
        eligible_accounts = con.execute(
            """
            SELECT COUNT(*) FROM gold_dim_accounts
            WHERE CAST(CreatedDate AS DATE) <= DATE '2026-07-11'
            """
        ).fetchone()[0]
        assert eligible_accounts == 16
        adopters = con.execute(
            """
            SELECT COUNT(DISTINCT AccountId) FROM gold_fact_feature_adoption_account
            WHERE ReportContext = 'AS_OF' AND AttributionPopulation = 'OFFICIAL'
            """
        ).fetchone()[0]
        assert adopters == 15
        assert adopters < 120
    finally:
        con.close()


def test_retention_denominator_maturity(ws13_db: Path) -> None:
    con = duckdb.connect(str(ws13_db), read_only=True)
    try:
        row = con.execute(
            """
            SELECT EligibleEntities, RetainedEntities
            FROM gold_fact_retention_cohort
            WHERE ReportContext = 'AS_OF' AND EntityType = 'ACCOUNT'
              AND RetentionWindow = 'D7'
            """
        ).fetchone()
        assert row[0] >= 0
        assert row[1] <= row[0]
    finally:
        con.close()


def test_retention_asof_engagement_excludes_post_asof_days(ws13_db: Path) -> None:
    con = duckdb.connect(str(ws13_db), read_only=True)
    try:
        post = con.execute(
            """
            SELECT COALESCE(SUM(ActiveEntityCount), 0)
            FROM gold_fact_engagement_periodic
            WHERE ReportContext = 'AS_OF' AND PeriodType = 'DAY'
              AND PeriodStartDate > DATE '2026-07-11'
            """
        ).fetchone()[0]
        assert post == 0
    finally:
        con.close()


def test_funnel_descriptive_labels(ws13_db: Path) -> None:
    con = duckdb.connect(str(ws13_db), read_only=True)
    try:
        labels = {
            r[0]
            for r in con.execute(
                "SELECT DISTINCT FunnelInterpretation FROM gold_fact_account_workflow_funnel"
            ).fetchall()
        }
        assert labels == {"DESCRIPTIVE_NON_CAUSAL"}
        asof_eligible = con.execute(
            """
            SELECT EligibleAccounts FROM gold_fact_account_workflow_funnel
            WHERE ReportContext = 'AS_OF' LIMIT 1
            """
        ).fetchone()[0]
        assert asof_eligible == 16
    finally:
        con.close()


def test_segment_totals_reconcile(ws13_db: Path) -> None:
    con = duckdb.connect(str(ws13_db), read_only=True)
    try:
        rows = con.execute(
            """
            SELECT Segment, EligibleAccounts FROM gold_fact_segment_product_metrics
            WHERE ReportContext = 'AS_OF' ORDER BY Segment
            """
        ).fetchall()
        assert sum(r[1] for r in rows) == 16
        segs = dict(rows)
        assert segs.get("SMB", 0) + segs.get("MID-MARKET", 0) == 16
    finally:
        con.close()


def test_activation_unchanged(ws13_db: Path) -> None:
    con = duckdb.connect(str(ws13_db), read_only=True)
    try:
        assert con.execute(
            "SELECT SUM(CASE WHEN IsActivated THEN 1 ELSE 0 END) FROM gold_fact_advanced_activation"
        ).fetchone()[0] == 21
        assert con.execute(
            """
            SELECT SUM(CASE WHEN IsEligibleAsOf AND IsActivatedAsOf THEN 1 ELSE 0 END),
                   SUM(CASE WHEN IsEligibleAsOf THEN 1 ELSE 0 END)
            FROM gold_fact_activation_as_of
            """
        ).fetchone() == (0, 15)
    finally:
        con.close()
