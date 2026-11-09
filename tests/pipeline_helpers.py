"""
Shared temporary DuckDB pipeline helpers (never touches authoritative DB).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import duckdb

REPO_ROOT = Path(__file__).resolve().parents[1]
SQL = REPO_ROOT / "sql"
GEO_XLSX = SQL / "data" / "raw_geography.xlsx"


def bootstrap_geography_derived_fixture(db_path: Path) -> None:
    sys.path.insert(0, str(SQL))
    from pipeline.geography import apply_derived_geography_fixture

    apply_derived_geography_fixture(db_path)


def run_script(script: Path, db_path: Path) -> None:
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


def bootstrap_geography_if_missing(db_path: Path) -> None:
    """raw_geography.xlsx is not in repo; stub geography from account country codes."""
    if GEO_XLSX.is_file():
        run_script(SQL / "bronze" / "bronze_geography.py", db_path)
        run_script(SQL / "silver" / "silver_geography.py", db_path)
        return
    bootstrap_geography_derived_fixture(db_path)


def run_attribution_pipeline(db_path: Path) -> None:
    run_script(SQL / "load_raw.py", db_path)
    run_script(SQL / "bronze" / "bronze_accounts.py", db_path)
    run_script(SQL / "bronze" / "bronze_users.py", db_path)
    run_script(SQL / "bronze" / "bronze_product_events.py", db_path)
    bootstrap_geography_if_missing(db_path)
    run_script(SQL / "silver" / "silver_accounts.py", db_path)
    run_script(SQL / "silver" / "silver_users.py", db_path)
    run_script(SQL / "silver" / "silver_product_events.py", db_path)
    run_script(SQL / "gold" / "gold_dim_accounts.py", db_path)
    run_script(SQL / "gold" / "gold_dim_users.py", db_path)
    run_script(SQL / "gold" / "gold_fact_product_events.py", db_path)


def run_minimal_event_pipeline(db_path: Path) -> None:
    """Bronze/Silver/Gold product events with account attribution dependencies."""
    run_script(SQL / "load_raw.py", db_path)
    run_script(SQL / "bronze" / "bronze_accounts.py", db_path)
    run_script(SQL / "bronze" / "bronze_users.py", db_path)
    run_script(SQL / "bronze" / "bronze_product_events.py", db_path)
    run_script(SQL / "silver" / "silver_users.py", db_path)
    run_script(SQL / "silver" / "silver_product_events.py", db_path)


def run_ws6_gold_pipeline(db_path: Path) -> None:
    """Silver product events through Gold detail and aggregated facts."""
    run_minimal_event_pipeline(db_path)
    run_script(SQL / "gold" / "gold_fact_product_events.py", db_path)
    run_script(SQL / "gold" / "gold_fact_product_events_aggregated.py", db_path)


def run_lifecycle_pipeline(db_path: Path) -> None:
    """Bronze/Silver/Gold dims, deals, product events, and activation (temp DB)."""
    run_script(SQL / "load_raw.py", db_path)
    run_script(SQL / "bronze" / "bronze_accounts.py", db_path)
    run_script(SQL / "bronze" / "bronze_users.py", db_path)
    run_script(SQL / "bronze" / "bronze_deals.py", db_path)
    run_script(SQL / "bronze" / "bronze_product_events.py", db_path)
    bootstrap_geography_if_missing(db_path)
    run_script(SQL / "silver" / "silver_geography.py", db_path)
    run_script(SQL / "silver" / "silver_accounts.py", db_path)
    run_script(SQL / "silver" / "silver_users.py", db_path)
    run_script(SQL / "silver" / "silver_deals.py", db_path)
    run_script(SQL / "silver" / "silver_product_events.py", db_path)
    run_script(SQL / "gold" / "gold_dim_accounts.py", db_path)
    run_script(SQL / "gold" / "gold_dim_users.py", db_path)
    run_script(SQL / "gold" / "gold_fact_deals.py", db_path)
    run_script(SQL / "gold" / "gold_fact_product_events.py", db_path)
    run_script(SQL / "gold" / "gold_fact_advanced_activation.py", db_path)
    run_script(SQL / "gold" / "gold_fact_activation_as_of.py", db_path)


def run_ws12_gold_analytics(db_path: Path) -> None:
    """WS-12/WS-13 product analytics Gold models (after product events + dims)."""
    run_script(SQL / "gold" / "gold_fact_qualified_product_events.py", db_path)
    run_script(SQL / "gold" / "gold_fact_engagement_periodic.py", db_path)
    run_script(SQL / "gold" / "gold_fact_feature_adoption_account.py", db_path)
    run_script(SQL / "gold" / "gold_fact_feature_adoption_user.py", db_path)
    run_script(SQL / "gold" / "gold_fact_feature_adoption_by_period.py", db_path)
    run_script(SQL / "gold" / "gold_fact_feature_breadth.py", db_path)
    run_script(SQL / "gold" / "gold_fact_product_activity_recency.py", db_path)
    run_script(SQL / "gold" / "gold_fact_retention_cohort.py", db_path)
    run_script(SQL / "gold" / "gold_fact_account_workflow_funnel.py", db_path)


def run_full_dq_pipeline(db_path: Path) -> None:
    """End-to-end Bronze/Silver/Gold used by WS-9 warehouse contracts (temp DB only)."""
    run_lifecycle_pipeline(db_path)
    run_ws12_gold_analytics(db_path)
    run_script(SQL / "gold" / "gold_fact_product_events_aggregated.py", db_path)
    run_script(SQL / "gold" / "gold_fact_segment_product_metrics.py", db_path)
    run_script(SQL / "gold" / "gold_dim_geography.py", db_path)
