"""
WS-9 cross-layer data quality and metric reconciliation contracts (temp DuckDB only).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import duckdb
import pytest

from pipeline_helpers import REPO_ROOT, run_full_dq_pipeline

sys.path.insert(0, str(REPO_ROOT / "sql"))
from gold_table_schemas import GOLD_FACT_ACTIVATION_AS_OF_COLUMNS  # noqa: E402

MANIFEST_PATH = REPO_ROOT / "data" / "source_snapshot" / "MANIFEST.json"
CANONICAL_EVENT_NAMES = (
    "create_deal",
    "enable_automation",
    "invite_user",
    "log_activity",
    "login",
    "move_deal_stage",
    "view_dashboard",
)


@pytest.fixture
def warehouse_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("PULSEIQ_AS_OF_DATE", "2026-07-11")
    db_path = tmp_path / "pulseiq_ws9.duckdb"
    monkeypatch.setenv("PULSEIQ_DB_PATH", str(db_path))
    run_full_dq_pipeline(db_path)
    return db_path


def test_raw_snapshot_manifest_counts(warehouse_db: Path) -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    expected = {t["source_table"]: t["row_count"] for t in manifest["tables"]}
    con = duckdb.connect(str(warehouse_db), read_only=True)
    try:
        for table, count in expected.items():
            actual = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            assert actual == count, table
    finally:
        con.close()


def _manifest_issue_count(issue: dict) -> int:
    if "count" in issue:
        return int(issue["count"])
    if "duplicate_identifier_rows" in issue:
        return int(issue["duplicate_identifier_rows"])
    raise KeyError(issue)


def test_known_source_data_quality_documented(warehouse_db: Path) -> None:
    """Manifest-documented issues are not unexpected failures."""
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    issues = {
        i["issue"]: _manifest_issue_count(i)
        for i in manifest.get("known_data_quality_issues", [])
    }
    con = duckdb.connect(str(warehouse_db), read_only=True)
    try:
        assert con.execute(
            "SELECT COUNT(*) FROM raw__product_events WHERE event_id IS NULL"
        ).fetchone()[0] == issues["null_event_id"]
        assert con.execute(
            "SELECT COUNT(*) FROM raw__product_events WHERE account_id IS NULL"
        ).fetchone()[0] == issues["null_account_id"]
        dup_groups = con.execute(
            """
            SELECT COUNT(*) FROM (
              SELECT deal_id FROM raw__deals GROUP BY deal_id HAVING COUNT(*) > 1
            )
            """
        ).fetchone()[0]
        assert dup_groups == issues["duplicate_deal_id_values"]
    finally:
        con.close()


def test_bronze_preserves_raw_grain(warehouse_db: Path) -> None:
    con = duckdb.connect(str(warehouse_db), read_only=True)
    try:
        assert con.execute("SELECT COUNT(*) FROM bronze_product_events").fetchone()[0] == 61747
        assert con.execute("SELECT COUNT(*) FROM bronze_accounts").fetchone()[0] == 120
        assert con.execute("SELECT COUNT(*) FROM bronze_users").fetchone()[0] == 400
        assert con.execute("SELECT COUNT(*) FROM bronze_deals").fetchone()[0] == 6443
    finally:
        con.close()


def test_silver_event_and_attribution_contract(warehouse_db: Path) -> None:
    con = duckdb.connect(str(warehouse_db), read_only=True)
    try:
        assert con.execute("SELECT COUNT(*) FROM silver_product_events").fetchone()[0] == 60552
        assert con.execute(
            "SELECT COUNT(*) FROM silver_product_events WHERE event_sk IS NULL"
        ).fetchone()[0] == 0
        assert con.execute(
            "SELECT COUNT(DISTINCT event_sk) FROM silver_product_events"
        ).fetchone()[0] == 60552

        statuses = dict(
            con.execute(
                """
                SELECT account_resolution_status, COUNT(*)
                FROM silver_product_events
                GROUP BY 1
                """
            ).fetchall()
        )
        assert statuses["SOURCE_VERIFIED"] == 59911
        assert statuses["ENRICHED"] == 226
        assert statuses["QUARANTINED"] == 415

        names = [
            r[0]
            for r in con.execute(
                "SELECT DISTINCT event_name_normalized FROM silver_product_events ORDER BY 1"
            ).fetchall()
        ]
        assert names == list(CANONICAL_EVENT_NAMES)
    finally:
        con.close()


def test_bronze_to_silver_event_reconciliation(warehouse_db: Path) -> None:
    con = duckdb.connect(str(warehouse_db), read_only=True)
    try:
        bronze_n = con.execute("SELECT COUNT(*) FROM bronze_product_events").fetchone()[0]
        silver_n = con.execute("SELECT COUNT(*) FROM silver_product_events").fetchone()[0]
        test_removed = con.execute(
            "SELECT COUNT(*) FROM bronze_product_events WHERE is_test_event"
        ).fetchone()[0]
        assert bronze_n - test_removed == silver_n == 60552
        assert test_removed == 1195
    finally:
        con.close()


def test_gold_detail_and_aggregated_reconciliation(warehouse_db: Path) -> None:
    con = duckdb.connect(str(warehouse_db), read_only=True)
    try:
        detail = con.execute("SELECT COUNT(*) FROM gold_fact_product_events").fetchone()[0]
        assert detail == 60552
        agg_sum = con.execute(
            "SELECT COALESCE(SUM(EventCount), 0) FROM gold_fact_product_events_aggregated"
        ).fetchone()[0]
        assert agg_sum == detail
        assert con.execute(
            "SELECT COUNT(DISTINCT EventSk) FROM gold_fact_product_events"
        ).fetchone()[0] == detail
    finally:
        con.close()


def test_activation_and_as_of_metric_contracts(warehouse_db: Path) -> None:
    con = duckdb.connect(str(warehouse_db), read_only=True)
    try:
        act = con.execute(
            """
            SELECT COUNT(*),
                   SUM(CASE WHEN IsActivated THEN 1 ELSE 0 END),
                   AVG(TimeToValueDays) FILTER (WHERE IsActivated),
                   approx_quantile(TimeToValueDays, 0.5) FILTER (WHERE IsActivated)
            FROM gold_fact_advanced_activation
            """
        ).fetchone()
        assert act[0] == 120 and act[1] == 21
        assert abs(float(act[2]) - 9.904761904761905) < 1e-6
        assert act[3] == 10

        asof = con.execute(
            """
            SELECT
                SUM(CASE WHEN IsEligibleAsOf THEN 1 ELSE 0 END),
                SUM(CASE WHEN IsEligibleAsOf AND IsActivatedAsOf THEN 1 ELSE 0 END),
                SUM(CASE WHEN TimeToValueDaysAsOf IS NOT NULL THEN 1 ELSE 0 END)
            FROM gold_fact_activation_as_of
            """
        ).fetchone()
        assert asof == (15, 0, 0)

        cols = [r[0] for r in con.execute("DESCRIBE gold_fact_activation_as_of").fetchall()]
        assert cols == list(GOLD_FACT_ACTIVATION_AS_OF_COLUMNS)
    finally:
        con.close()


def test_deal_duplicate_groups_contract(warehouse_db: Path) -> None:
    con = duckdb.connect(str(warehouse_db), read_only=True)
    try:
        dup_groups = con.execute(
            """
            SELECT COUNT(*) FROM (
                SELECT deal_id FROM raw__deals GROUP BY 1 HAVING COUNT(*) > 1
            )
            """
        ).fetchone()[0]
        assert dup_groups == 35

        multi_account = con.execute(
            """
            SELECT COUNT(*) FROM (
                SELECT deal_id FROM raw__deals
                GROUP BY 1 HAVING COUNT(DISTINCT account_id) > 1
            )
            """
        ).fetchone()[0]
        assert multi_account == 0

        assert con.execute("SELECT COUNT(*) FROM silver_deals").fetchone()[0] == 6443
        assert con.execute("SELECT COUNT(*) FROM gold_fact_deals").fetchone()[0] == 6443
    finally:
        con.close()


def test_attribution_partition_equals_silver_grain(warehouse_db: Path) -> None:
    con = duckdb.connect(str(warehouse_db), read_only=True)
    try:
        parts = con.execute(
            """
            SELECT account_resolution_status, COUNT(*) FROM silver_product_events
            GROUP BY 1
            """
        ).fetchall()
        total = sum(c for _, c in parts)
        assert total == 59911 + 226 + 415 == 60552
    finally:
        con.close()


def test_default_as_of_date_on_dimensions(warehouse_db: Path) -> None:
    con = duckdb.connect(str(warehouse_db), read_only=True)
    try:
        assert con.execute(
            "SELECT COUNT(*) FROM silver_accounts WHERE is_future_created"
        ).fetchone()[0] == 104
        assert con.execute(
            "SELECT COUNT(*) FROM gold_fact_activation_as_of WHERE ReportAsOfDate = DATE '2026-07-11'"
        ).fetchone()[0] == 120
    finally:
        con.close()
