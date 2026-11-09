"""
WS-6 feature property extraction tests (temporary DuckDB only).
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

from pipeline_helpers import REPO_ROOT, run_script, run_ws6_gold_pipeline

SQL = REPO_ROOT / "sql"

EXPECTED_FEATURES = ("automation", "dashboard", "deal", "pipeline")
EXPECTED_EVENT_SOURCES = ("api", "automation", "ui")


@pytest.fixture
def feature_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "pulseiq_ws6.duckdb"
    run_ws6_gold_pipeline(db_path)
    return db_path


def test_event_properties_preserved_in_gold(feature_db: Path) -> None:
    con = duckdb.connect(str(feature_db), read_only=True)
    try:
        mismatch = con.execute(
            """
            SELECT COUNT(*)
            FROM gold_fact_product_events g
            INNER JOIN silver_product_events s ON g."EventSk" = s.event_sk
            WHERE g."EventProperties" IS DISTINCT FROM s.event_properties
            """
        ).fetchone()[0]
        assert mismatch == 0
        assert con.execute(
            'SELECT COUNT(*) FROM gold_fact_product_events WHERE "EventProperties" IS NULL'
        ).fetchone()[0] == 0
    finally:
        con.close()


def test_extracted_columns_match_json(feature_db: Path) -> None:
    con = duckdb.connect(str(feature_db), read_only=True)
    try:
        bad = con.execute(
            """
            SELECT COUNT(*)
            FROM silver_product_events
            WHERE event_properties_parse_status = 'OK'
              AND (
                feature_name IS DISTINCT FROM
                    json_extract_string(TRY_CAST(event_properties AS JSON), '$.feature_name')
                OR event_source IS DISTINCT FROM
                    json_extract_string(TRY_CAST(event_properties AS JSON), '$.source')
                OR pipeline_id IS DISTINCT FROM
                    json_extract_string(TRY_CAST(event_properties AS JSON), '$.pipeline_id')
                OR stage_id IS DISTINCT FROM
                    json_extract_string(TRY_CAST(event_properties AS JSON), '$.stage_id')
              )
            """
        ).fetchone()[0]
        assert bad == 0

        missing_pipeline = con.execute(
            """
            SELECT COUNT(*) FROM silver_product_events
            WHERE pipeline_id IS NULL AND stage_id IS NULL
            """
        ).fetchone()[0]
        assert missing_pipeline == 60552 - 24156
    finally:
        con.close()


def test_invalid_json_handling(feature_db: Path) -> None:
    con = duckdb.connect(str(feature_db), read_only=True)
    try:
        assert con.execute(
            """
            SELECT event_properties_parse_status, COUNT(*)
            FROM silver_product_events
            GROUP BY 1
            ORDER BY 1
            """
        ).fetchall() == [("OK", 60552)]

        status = con.execute(
            """
            SELECT
                CASE
                    WHEN payload IS NULL THEN 'NULL_PAYLOAD'
                    WHEN TRY_CAST(payload AS JSON) IS NULL THEN 'INVALID_JSON'
                    ELSE 'OK'
                END AS st,
                CASE
                    WHEN payload IS NULL THEN NULL
                    WHEN TRY_CAST(payload AS JSON) IS NULL THEN NULL
                    ELSE json_extract_string(TRY_CAST(payload AS JSON), '$.feature_name')
                END AS feature_name
            FROM (SELECT 'not-json' AS payload)
            """
        ).fetchone()
        assert status == ("INVALID_JSON", None)
    finally:
        con.close()


def test_grain_and_attribution_intact(feature_db: Path) -> None:
    con = duckdb.connect(str(feature_db), read_only=True)
    try:
        assert con.execute("SELECT COUNT(*) FROM silver_product_events").fetchone()[0] == 60552
        assert con.execute(
            "SELECT COUNT(DISTINCT event_sk) FROM silver_product_events"
        ).fetchone()[0] == 60552
        assert con.execute(
            """
            SELECT COUNT(*) FROM silver_product_events
            WHERE account_resolution_status = 'SOURCE_VERIFIED'
            """
        ).fetchone()[0] == 59911
    finally:
        con.close()


def test_gold_detail_feature_columns(feature_db: Path) -> None:
    con = duckdb.connect(str(feature_db), read_only=True)
    try:
        cols = {r[0] for r in con.execute("DESCRIBE gold_fact_product_events").fetchall()}
        for name in (
            "FeatureName",
            "EventSource",
            "PipelineId",
            "StageId",
            "EventProperties",
        ):
            assert name in cols

        features = tuple(
            r[0]
            for r in con.execute(
                """
                SELECT DISTINCT "FeatureName"
                FROM gold_fact_product_events
                ORDER BY 1
                """
            ).fetchall()
        )
        assert features == EXPECTED_FEATURES
    finally:
        con.close()


def test_aggregated_grain_and_reconciliation(feature_db: Path) -> None:
    con = duckdb.connect(str(feature_db), read_only=True)
    try:
        agg_cols = [
            r[0] for r in con.execute("DESCRIBE gold_fact_product_events_aggregated").fetchall()
        ]
        assert "FeatureName" in agg_cols

        detail_n = con.execute("SELECT COUNT(*) FROM gold_fact_product_events").fetchone()[0]
        agg_sum = con.execute(
            "SELECT COALESCE(SUM(EventCount), 0) FROM gold_fact_product_events_aggregated"
        ).fetchone()[0]
        assert detail_n == 60552
        assert agg_sum == detail_n

        agg_rows = con.execute(
            "SELECT COUNT(*) FROM gold_fact_product_events_aggregated"
        ).fetchone()[0]
        assert agg_rows == 49300
    finally:
        con.close()


def test_no_duplication_from_extraction(feature_db: Path) -> None:
    con = duckdb.connect(str(feature_db), read_only=True)
    try:
        assert con.execute(
            """
            SELECT COUNT(*) FROM (
                SELECT event_sk, feature_name, event_source, pipeline_id, stage_id
                FROM silver_product_events
            )
            """
        ).fetchone()[0] == 60552
    finally:
        con.close()


def test_deterministic_rerun(tmp_path: Path) -> None:
    db_path = tmp_path / "ws6_det.duckdb"
    run_ws6_gold_pipeline(db_path)
    con = duckdb.connect(str(db_path), read_only=True)
    first = con.execute(
        'SELECT "EventSk", "FeatureName", "EventSource" FROM gold_fact_product_events ORDER BY 1'
    ).fetchall()
    con.close()

    run_script(SQL / "silver" / "silver_product_events.py", db_path)
    run_script(SQL / "gold" / "gold_fact_product_events.py", db_path)
    run_script(SQL / "gold" / "gold_fact_product_events_aggregated.py", db_path)

    con = duckdb.connect(str(db_path), read_only=True)
    second = con.execute(
        'SELECT "EventSk", "FeatureName", "EventSource" FROM gold_fact_product_events ORDER BY 1'
    ).fetchall()
    con.close()
    assert first == second


def test_event_source_distinct_from_source_system(feature_db: Path) -> None:
    con = duckdb.connect(str(feature_db), read_only=True)
    try:
        rows = con.execute(
            """
            SELECT DISTINCT "EventSource", "SourceSystem"
            FROM gold_fact_product_events
            ORDER BY 1, 2
            LIMIT 5
            """
        ).fetchall()
        assert len(rows) >= 3
        assert con.execute(
            """
            SELECT COUNT(DISTINCT "EventSource") FROM gold_fact_product_events
            """
        ).fetchone()[0] == len(EXPECTED_EVENT_SOURCES)
    finally:
        con.close()
