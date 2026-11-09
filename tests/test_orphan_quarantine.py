"""
WS-5.2 orphan account attribution and quarantine tests (temporary DuckDB only).
"""

from __future__ import annotations

import os
from pathlib import Path

import duckdb
import pytest

from pipeline_helpers import REPO_ROOT, run_attribution_pipeline, run_script

SQL = REPO_ROOT / "sql"


@pytest.fixture
def quarantine_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "pulseiq_ws52.duckdb"
    run_attribution_pipeline(db_path)
    return db_path


def test_row_grain_and_event_sk(quarantine_db: Path) -> None:
    con = duckdb.connect(str(quarantine_db), read_only=True)
    try:
        n = con.execute("SELECT COUNT(*) FROM silver_product_events").fetchone()[0]
        assert n == 60552
        assert con.execute(
            "SELECT COUNT(*) FROM silver_product_events WHERE event_sk IS NULL"
        ).fetchone()[0] == 0
        assert con.execute(
            "SELECT COUNT(DISTINCT event_sk) FROM silver_product_events"
        ).fetchone()[0] == n
    finally:
        con.close()


def test_attribution_status_counts(quarantine_db: Path) -> None:
    con = duckdb.connect(str(quarantine_db), read_only=True)
    try:
        verified = con.execute(
            """
            SELECT COUNT(*) FROM silver_product_events
            WHERE account_resolution_status = 'SOURCE_VERIFIED'
            """
        ).fetchone()[0]
        enriched = con.execute(
            """
            SELECT COUNT(*) FROM silver_product_events
            WHERE account_resolution_status = 'ENRICHED'
            """
        ).fetchone()[0]
        quarantined = con.execute(
            """
            SELECT COUNT(*) FROM silver_product_events
            WHERE account_resolution_status = 'QUARANTINED'
            """
        ).fetchone()[0]
        assert verified == 59911
        assert enriched == 226
        assert quarantined == 415
        assert verified + enriched + quarantined == 60552

        by_reason = dict(
            con.execute(
                """
                SELECT account_resolution_reason, COUNT(*)
                FROM silver_product_events
                WHERE account_id IS NULL
                GROUP BY 1
                """
            ).fetchall()
        )
        assert by_reason.get("USER_ACCOUNT_ONLY") == 216
        assert by_reason.get("DEAL_ACCOUNT_ONLY") == 10
        assert by_reason.get("CONFLICTING_USER_DEAL_ACCOUNTS") == 406
        assert by_reason.get("NO_VALID_ACCOUNT_REFERENCE") == 9
        assert sum(by_reason.values()) == 641

        invalid = con.execute(
            """
            SELECT COUNT(*) FROM silver_product_events
            WHERE account_resolution_reason = 'INVALID_SOURCE_ACCOUNT_REFERENCE'
            """
        ).fetchone()[0]
        assert invalid == 0
    finally:
        con.close()


def test_original_account_id_preserved(quarantine_db: Path) -> None:
    con = duckdb.connect(str(quarantine_db), read_only=True)
    try:
        orphans = con.execute(
            """
            SELECT COUNT(*) FROM silver_product_events
            WHERE account_id IS NULL
              AND account_id_resolved IS NOT NULL
            """
        ).fetchone()[0]
        assert orphans == 226
        overwritten = con.execute(
            """
            SELECT COUNT(*) FROM silver_product_events
            WHERE account_id IS NOT NULL
              AND account_id <> account_id_resolved
            """
        ).fetchone()[0]
        assert overwritten == 0
    finally:
        con.close()


def test_enriched_and_quarantine_rules(quarantine_db: Path) -> None:
    con = duckdb.connect(str(quarantine_db), read_only=True)
    try:
        user_only = con.execute(
            """
            SELECT COUNT(*) FROM silver_product_events
            WHERE account_resolution_reason = 'USER_ACCOUNT_ONLY'
              AND account_resolution_status = 'ENRICHED'
              AND account_resolution_method = 'USER_DIM'
              AND account_id IS NULL
              AND account_id_resolved IS NOT NULL
            """
        ).fetchone()[0]
        assert user_only == 216

        deal_only = con.execute(
            """
            SELECT COUNT(*) FROM silver_product_events
            WHERE account_resolution_reason = 'DEAL_ACCOUNT_ONLY'
              AND account_resolution_status = 'ENRICHED'
              AND account_resolution_method = 'DEAL_RAW'
              AND account_id IS NULL
              AND account_id_resolved IS NOT NULL
            """
        ).fetchone()[0]
        assert deal_only == 10

        conflicting = con.execute(
            """
            SELECT COUNT(*) FROM silver_product_events
            WHERE account_resolution_reason = 'CONFLICTING_USER_DEAL_ACCOUNTS'
              AND account_resolution_status = 'QUARANTINED'
              AND account_id_resolved IS NULL
            """
        ).fetchone()[0]
        assert conflicting == 406

        unresolved = con.execute(
            """
            SELECT COUNT(*) FROM silver_product_events
            WHERE account_resolution_reason = 'NO_VALID_ACCOUNT_REFERENCE'
              AND account_resolution_status = 'QUARANTINED'
              AND account_id_resolved IS NULL
            """
        ).fetchone()[0]
        assert unresolved == 9

        bad_enrich = con.execute(
            """
            SELECT COUNT(*) FROM silver_product_events
            WHERE account_resolution_reason = 'CONFLICTING_USER_DEAL_ACCOUNTS'
              AND account_resolution_status = 'ENRICHED'
            """
        ).fetchone()[0]
        assert bad_enrich == 0
    finally:
        con.close()


def test_resolved_accounts_in_dim(quarantine_db: Path) -> None:
    con = duckdb.connect(str(quarantine_db), read_only=True)
    try:
        orphan_refs = con.execute(
            """
            SELECT COUNT(*) FROM silver_product_events e
            WHERE e.account_id_resolved IS NOT NULL
              AND NOT EXISTS (
                SELECT 1 FROM gold_dim_accounts a
                WHERE a."AccountId" = e.account_id_resolved
              )
            """
        ).fetchone()[0]
        assert orphan_refs == 0

        verified_refs = con.execute(
            """
            SELECT COUNT(*) FROM silver_product_events e
            WHERE e.account_resolution_status = 'SOURCE_VERIFIED'
              AND NOT EXISTS (
                SELECT 1 FROM gold_dim_accounts a
                WHERE a."AccountId" = e.account_id
              )
            """
        ).fetchone()[0]
        assert verified_refs == 0
    finally:
        con.close()


def test_quarantine_view_and_deal_join_grain(quarantine_db: Path) -> None:
    con = duckdb.connect(str(quarantine_db), read_only=True)
    try:
        q_view = con.execute(
            "SELECT COUNT(*) FROM silver_product_events_quarantine"
        ).fetchone()[0]
        assert q_view == 415

        silver_n = con.execute("SELECT COUNT(*) FROM silver_product_events").fetchone()[0]
        assert silver_n == 60552

        orphan_naive = con.execute(
            """
            SELECT COUNT(*)
            FROM silver_product_events e
            INNER JOIN raw__deals d ON e.deal_id = d.deal_id
            WHERE e.account_id IS NULL
            """
        ).fetchone()[0]
        orphans_with_deal = con.execute(
            """
            SELECT COUNT(*) FROM silver_product_events
            WHERE account_id IS NULL AND deal_id IS NOT NULL
            """
        ).fetchone()[0]
        assert orphans_with_deal == 416
        assert orphan_naive == orphans_with_deal + 4
    finally:
        con.close()


def test_gold_detail_exposes_resolution(quarantine_db: Path) -> None:
    con = duckdb.connect(str(quarantine_db), read_only=True)
    try:
        assert con.execute("SELECT COUNT(*) FROM gold_fact_product_events").fetchone()[0] == 60552
        cols = {
            row[0]
            for row in con.execute("DESCRIBE gold_fact_product_events").fetchall()
        }
        assert {
            "AccountId",
            "AccountIdResolved",
            "AccountResolutionStatus",
            "AccountResolutionMethod",
            "AccountResolutionReason",
        }.issubset(cols)

        quarantine_in_gold = con.execute(
            """
            SELECT COUNT(*) FROM gold_fact_product_events
            WHERE "AccountResolutionStatus" = 'QUARANTINED'
            """
        ).fetchone()[0]
        assert quarantine_in_gold == 415
    finally:
        con.close()


def test_deterministic_rerun(tmp_path: Path) -> None:
    db_a = tmp_path / "a.duckdb"
    db_b = tmp_path / "b.duckdb"
    run_attribution_pipeline(db_a)
    run_attribution_pipeline(db_b)

    con_a = duckdb.connect(str(db_a), read_only=True)
    con_b = duckdb.connect(str(db_b), read_only=True)
    try:
        sk_a = con_a.execute(
            "SELECT event_sk, account_id_resolved, account_resolution_status, "
            "account_resolution_method, account_resolution_reason "
            "FROM silver_product_events ORDER BY event_sk"
        ).fetchall()
        sk_b = con_b.execute(
            "SELECT event_sk, account_id_resolved, account_resolution_status, "
            "account_resolution_method, account_resolution_reason "
            "FROM silver_product_events ORDER BY event_sk"
        ).fetchall()
        assert sk_a == sk_b
    finally:
        con_a.close()
        con_b.close()


def test_legacy_event_columns_present(quarantine_db: Path) -> None:
    con = duckdb.connect(str(quarantine_db), read_only=True)
    try:
        sample = con.execute(
            """
            SELECT event_properties, event_name, event_name_normalized, platform
            FROM silver_product_events
            LIMIT 1
            """
        ).fetchone()
        assert sample is not None
        q_cols = {
            row[0]
            for row in con.execute(
                "DESCRIBE silver_product_events_quarantine"
            ).fetchall()
        }
        for col in (
            "event_sk",
            "account_id",
            "account_id_resolved",
            "user_id",
            "deal_id",
            "event_name_normalized",
            "account_resolution_status",
            "account_resolution_method",
            "account_resolution_reason",
            "event_properties",
        ):
            assert col in q_cols
    finally:
        con.close()


def test_authoritative_db_not_used(quarantine_db: Path) -> None:
    auth = REPO_ROOT / "product_analytics_light.db"
    if auth.is_file():
        mtime_before = auth.stat().st_mtime
    run_script(SQL / "silver" / "silver_product_events.py", quarantine_db)
    if auth.is_file():
        assert auth.stat().st_mtime == mtime_before
