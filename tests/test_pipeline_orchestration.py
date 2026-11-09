"""
WS-10 pipeline orchestration tests (isolated temp DB and directories).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import duckdb
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
RUN_PIPELINE = REPO_ROOT / "run_pipeline.py"
SQL = REPO_ROOT / "sql"

sys.path.insert(0, str(SQL))
from pipeline.safety import authoritative_db_path, resolve_pipeline_db_path  # noqa: E402
from pipeline.geography import GeographyMode, geography_excel_available  # noqa: E402
from pipeline.runner import PipelineRunner, planned_stage_ids, validate_prerequisites  # noqa: E402
from pipeline.stages import STAGE_LOAD_RAW  # noqa: E402


def _run_cli(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    full_env = os.environ.copy()
    if env:
        full_env.update(env)
    return subprocess.run(
        [sys.executable, str(RUN_PIPELINE), *args],
        cwd=str(REPO_ROOT),
        env=full_env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_dry_run_execution_order() -> None:
    proc = _run_cli("--dry-run", "--geography-mode", "derived-fixture")
    assert proc.returncode == 0, proc.stderr or proc.stdout
    expected_tail = planned_stage_ids(geography_mode="derived-fixture")
    for stage_id in expected_tail:
        assert f"would run: {stage_id}" in proc.stdout


def test_missing_db_path_rejected() -> None:
    env = os.environ.copy()
    env.pop("PULSEIQ_DB_PATH", None)
    proc = subprocess.run(
        [sys.executable, str(RUN_PIPELINE)],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 2
    assert "Database path is required" in proc.stderr


def test_authoritative_db_protection() -> None:
    auth = authoritative_db_path()
    if not auth.is_file():
        pytest.skip("authoritative db not present in workspace")
    with pytest.raises(ValueError, match="Refusing to modify authoritative"):
        resolve_pipeline_db_path(cli_db_path=auth, require_explicit=True)


def test_reporting_date_cli_precedence(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PULSEIQ_AS_OF_DATE", "2025-01-01")
    db = tmp_path / "t.duckdb"
    runner = PipelineRunner(
        db,
        as_of_date="2026-07-11",
        geography_mode=GeographyMode.DERIVED_FIXTURE,
        export_dir=tmp_path / "csv",
        dry_run=True,
    )
    result = runner.run()
    assert result.as_of_date == "2026-07-11"


def test_geography_source_mode_requires_excel(tmp_path: Path) -> None:
    if geography_excel_available():
        pytest.skip("source excel present; cannot assert missing-file failure")
    db = tmp_path / "t.duckdb"
    runner = PipelineRunner(
        db,
        as_of_date="2026-07-11",
        geography_mode=GeographyMode.SOURCE,
        export_dir=tmp_path / "csv",
        dry_run=False,
    )
    result = runner.run()
    assert result.status == "failed"
    assert result.failure and "geography" in str(result.failure).lower()


def test_derived_fixture_mode_e2e(tmp_path: Path) -> None:
    db = tmp_path / "pulse.duckdb"
    export_dir = tmp_path / "gold_csv"
    report_dir = tmp_path / "reports"
    proc = _run_cli(
        "--db-path",
        str(db),
        "--export-dir",
        str(export_dir),
        "--as-of-date",
        "2026-07-11",
        "--geography-mode",
        "derived-fixture",
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert db.is_file()
    con = duckdb.connect(str(db), read_only=True)
    try:
        assert con.execute("SELECT COUNT(*) FROM silver_product_events").fetchone()[0] == 60552
        assert con.execute(
            "SELECT SUM(CASE WHEN IsActivated THEN 1 ELSE 0 END) FROM gold_fact_advanced_activation"
        ).fetchone()[0] == 21
    finally:
        con.close()
    for csv_name in (
        "fact_product_events.csv",
        "fact_activation_as_of.csv",
        "fact_advanced_activation.csv",
    ):
        assert (export_dir / csv_name).is_file()


def test_stage_failure_stops_pipeline(tmp_path: Path) -> None:
    db = tmp_path / "fail.duckdb"
    bad_snap = tmp_path / "empty_snapshot"
    bad_snap.mkdir()
    runner = PipelineRunner(
        db,
        as_of_date="2026-07-11",
        geography_mode=GeographyMode.DERIVED_FIXTURE,
        export_dir=tmp_path / "csv",
        snapshot_dir=bad_snap,
        report_dir=tmp_path / "reports",
    )
    result = runner.run()
    assert result.status == "failed"
    assert not any(s.stage_id == STAGE_LOAD_RAW.stage_id and s.status == "ok" for s in result.stages)


def test_pipeline_report_written(tmp_path: Path) -> None:
    db = tmp_path / "pulse2.duckdb"
    export_dir = tmp_path / "gold_csv"
    report_dir = tmp_path / "reports"
    runner = PipelineRunner(
        db,
        as_of_date="2026-07-11",
        geography_mode=GeographyMode.DERIVED_FIXTURE,
        export_dir=export_dir,
        report_dir=report_dir,
    )
    result = runner.run()
    assert result.status == "success"
    reports = list(report_dir.glob("*.json"))
    assert reports
    payload = json.loads(reports[0].read_text(encoding="utf-8"))
    assert payload["run_id"] == result.run_id
    assert payload["dq"]["passed"] is True
    assert payload["row_counts"]["silver_product_events"] == 60552


def test_repeated_execution_idempotent(tmp_path: Path) -> None:
    db = tmp_path / "repeat.duckdb"
    export_dir = tmp_path / "gold_csv"
    args = [
        "--db-path",
        str(db),
        "--export-dir",
        str(export_dir),
        "--geography-mode",
        "derived-fixture",
    ]
    first = _run_cli(*args)
    second = _run_cli(*args)
    assert first.returncode == 0 and second.returncode == 0
    con = duckdb.connect(str(db), read_only=True)
    try:
        n = con.execute("SELECT COUNT(*) FROM gold_fact_product_events").fetchone()[0]
        assert n == 60552
    finally:
        con.close()


def test_prerequisites_valid() -> None:
    errors = validate_prerequisites()
    assert errors == []


def test_invalid_as_of_date() -> None:
    proc = _run_cli("--dry-run", "--as-of-date", "not-a-date", "--db-path", "artifacts/x.duckdb")
    assert proc.returncode == 2
