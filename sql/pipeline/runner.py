"""Execute PulseIQ pipeline stages with reporting and failure handling."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from db_config import DEFAULT_AS_OF_DATE, get_repo_root

from pipeline.dq_validation import run_pipeline_dq
from pipeline.export_validation import validate_gold_exports
from pipeline.geography import (
    GeographyMode,
    apply_derived_geography_fixture,
    geography_excel_available,
)
from pipeline.stages import (
    BRONZE_STAGES,
    GOLD_STAGES,
    SILVER_STAGES,
    STAGE_DQ,
    STAGE_EXPORT,
    STAGE_EXPORT_VALIDATE,
    STAGE_GEOGRAPHY,
    STAGE_LOAD_RAW,
    STAGE_VALIDATE_SNAPSHOT,
    planned_stage_ids,
)

REPO_ROOT = get_repo_root()
SQL = REPO_ROOT / "sql"
SNAPSHOT_DIR = REPO_ROOT / "data" / "source_snapshot"
DEFAULT_EXPORT_DIR = REPO_ROOT / "artifacts" / "gold_csv"
REPORT_DIR = REPO_ROOT / "artifacts" / "pipeline_runs"


@dataclass
class StageRecord:
    stage_id: str
    status: str
    duration_seconds: float
    message: str = ""


@dataclass
class PipelineRunResult:
    run_id: str
    started_at: str
    ended_at: str
    status: str
    database_path: str
    as_of_date: str
    geography_mode: str
    export_dir: str
    dry_run: bool
    stages: list[StageRecord] = field(default_factory=list)
    row_counts: dict[str, Any] = field(default_factory=dict)
    dq: dict[str, Any] = field(default_factory=dict)
    export_validation: dict[str, Any] = field(default_factory=dict)
    failure: dict[str, Any] | None = None


def validate_prerequisites(snapshot_dir: Path | None = None) -> list[str]:
    errors: list[str] = []
    snap = snapshot_dir or SNAPSHOT_DIR
    manifest = snap / "MANIFEST.json"
    if not manifest.is_file():
        errors.append(f"Missing {manifest}")
        return errors
    data = json.loads(manifest.read_text(encoding="utf-8"))
    for entry in data.get("tables", []):
        path = snap / entry["filename"]
        if not path.is_file():
            errors.append(f"Missing snapshot file: {path}")
    return errors


def _run_subprocess(
    script: Path,
    env: dict[str, str],
    *,
    extra_args: list[str] | None = None,
) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, str(script)]
    if extra_args:
        cmd.extend(extra_args)
    return subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def collect_row_counts(db_path: Path) -> dict[str, Any]:
    import duckdb

    con = duckdb.connect(str(db_path), read_only=True)
    try:
        return {
            "raw__product_events": con.execute(
                "SELECT COUNT(*) FROM raw__product_events"
            ).fetchone()[0],
            "silver_product_events": con.execute(
                "SELECT COUNT(*) FROM silver_product_events"
            ).fetchone()[0],
            "gold_fact_product_events": con.execute(
                "SELECT COUNT(*) FROM gold_fact_product_events"
            ).fetchone()[0],
            "gold_agg_event_count_sum": con.execute(
                "SELECT COALESCE(SUM(EventCount), 0) FROM gold_fact_product_events_aggregated"
            ).fetchone()[0],
        }
    finally:
        con.close()


class PipelineRunner:
    def __init__(
        self,
        db_path: Path,
        *,
        as_of_date: str,
        geography_mode: GeographyMode,
        export_dir: Path,
        snapshot_dir: Path | None = None,
        dry_run: bool = False,
        skip_dq: bool = False,
        report_dir: Path | None = None,
    ) -> None:
        self.db_path = db_path
        self.as_of_date = as_of_date
        self.geography_mode = geography_mode
        self.export_dir = export_dir
        self.snapshot_dir = snapshot_dir or SNAPSHOT_DIR
        self.dry_run = dry_run
        self.skip_dq = skip_dq
        self.report_dir = report_dir or REPORT_DIR
        self.run_id = uuid.uuid4().hex[:12]
        self.stages: list[StageRecord] = []

    def _base_env(self) -> dict[str, str]:
        env = os.environ.copy()
        env["PULSEIQ_DB_PATH"] = str(self.db_path)
        env["PULSEIQ_AS_OF_DATE"] = self.as_of_date
        env["PULSEIQ_EXPORT_DIR"] = str(self.export_dir)
        return env

    def _record(
        self,
        stage_id: str,
        status: str,
        duration: float,
        message: str = "",
    ) -> None:
        self.stages.append(
            StageRecord(stage_id=stage_id, status=status, duration_seconds=duration, message=message)
        )

    def run(self) -> PipelineRunResult:
        started = datetime.now(timezone.utc)
        print(f"PulseIQ pipeline run {self.run_id}")
        print(f"  Database (will be modified): {self.db_path}")
        print(f"  As-of date: {self.as_of_date}")
        print(f"  Geography mode: {self.geography_mode.value}")
        print(f"  Export directory: {self.export_dir}")
        if self.dry_run:
            print("  DRY RUN — no data modifications")

        prereq_errors = validate_prerequisites(self.snapshot_dir)
        if prereq_errors:
            return self._finalize(
                started,
                "failed",
                failure={"stage": "prerequisites", "errors": prereq_errors},
            )

        if self.geography_mode == GeographyMode.SOURCE and not geography_excel_available():
            return self._finalize(
                started,
                "failed",
                failure={
                    "stage": "geography",
                    "errors": [f"Geography source missing: {SQL / 'data' / 'raw_geography.xlsx'}"],
                },
            )

        if self.dry_run:
            for stage_id in planned_stage_ids(
                geography_mode=self.geography_mode.value,
                include_dq=not self.skip_dq,
            ):
                print(f"  [dry-run] would run: {stage_id}")
            return self._finalize(started, "dry_run")

        env = self._base_env()
        failure: dict[str, Any] | None = None

        def run_script_stage(stage_id: str, script: Path, extra: list[str] | None = None) -> bool:
            nonlocal failure
            t0 = time.perf_counter()
            proc = _run_subprocess(script, env, extra_args=extra)
            duration = time.perf_counter() - t0
            if proc.returncode != 0:
                msg = (proc.stderr or proc.stdout or "non-zero exit").strip()
                self._record(stage_id, "failed", duration, msg[:2000])
                print(f"FAILED {stage_id}: {msg}", file=sys.stderr)
                failure = {
                    "stage": stage_id,
                    "exit_code": proc.returncode,
                    "stderr": proc.stderr,
                    "stdout": proc.stdout,
                }
                return False
            self._record(stage_id, "ok", duration)
            print(f"OK {stage_id} ({duration:.1f}s)")
            return True

        # Stage 1 — validate + load
        t0 = time.perf_counter()
        proc = _run_subprocess(
            STAGE_VALIDATE_SNAPSHOT.script,
            env,
            extra_args=["--snapshot-dir", str(self.snapshot_dir)],
        )
        if proc.returncode != 0:
            self._record(STAGE_VALIDATE_SNAPSHOT.stage_id, "failed", time.perf_counter() - t0, proc.stderr)
            return self._finalize(
                started,
                "failed",
                failure={"stage": STAGE_VALIDATE_SNAPSHOT.stage_id, "stderr": proc.stderr},
            )
        self._record(STAGE_VALIDATE_SNAPSHOT.stage_id, "ok", time.perf_counter() - t0)

        if not run_script_stage(
            STAGE_LOAD_RAW.stage_id,
            STAGE_LOAD_RAW.script,
            ["--snapshot-dir", str(self.snapshot_dir), "--db-path", str(self.db_path)],
        ):
            return self._finalize(started, "failed", failure=failure)

        for stage in BRONZE_STAGES:
            if not run_script_stage(stage.stage_id, stage.script):
                return self._finalize(started, "failed", failure=failure)

        # Geography
        t0 = time.perf_counter()
        if self.geography_mode == GeographyMode.SOURCE:
            if not run_script_stage("bronze_geography", SQL / "bronze" / "bronze_geography.py"):
                return self._finalize(started, "failed", failure=failure)
        else:
            try:
                apply_derived_geography_fixture(self.db_path)
            except Exception as exc:
                self._record(STAGE_GEOGRAPHY.stage_id, "failed", time.perf_counter() - t0, str(exc))
                return self._finalize(
                    started,
                    "failed",
                    failure={"stage": STAGE_GEOGRAPHY.stage_id, "error": str(exc)},
                )
        self._record(STAGE_GEOGRAPHY.stage_id, "ok", time.perf_counter() - t0)
        print(f"OK {STAGE_GEOGRAPHY.stage_id} ({time.perf_counter() - t0:.1f}s)")

        for stage in SILVER_STAGES:
            if stage.stage_id == "silver_geography" and self.geography_mode != GeographyMode.SOURCE:
                continue
            if not run_script_stage(stage.stage_id, stage.script):
                return self._finalize(started, "failed", failure=failure)

        for stage in GOLD_STAGES:
            if not run_script_stage(stage.stage_id, stage.script):
                return self._finalize(started, "failed", failure=failure)

        self.export_dir.mkdir(parents=True, exist_ok=True)
        if not run_script_stage(STAGE_EXPORT.stage_id, STAGE_EXPORT.script):
            return self._finalize(started, "failed", failure=failure)

        row_counts = collect_row_counts(self.db_path)
        dq_summary: dict[str, Any] = {}
        export_val_summary: dict[str, Any] = {}

        if not self.skip_dq:
            t0 = time.perf_counter()
            dq = run_pipeline_dq(self.db_path)
            self._record(
                STAGE_DQ.stage_id,
                "ok" if dq.passed else "failed",
                time.perf_counter() - t0,
                "; ".join(dq.errors) if dq.errors else "",
            )
            dq_summary = {"passed": dq.passed, "checks": dq.checks, "errors": dq.errors}
            if not dq.passed:
                print(f"FAILED {STAGE_DQ.stage_id}: {dq.errors}", file=sys.stderr)
                return self._finalize(
                    started,
                    "failed",
                    row_counts=row_counts,
                    dq=dq_summary,
                    failure={"stage": STAGE_DQ.stage_id, "errors": dq.errors},
                )
            print(f"OK {STAGE_DQ.stage_id}")

            t0 = time.perf_counter()
            ev = validate_gold_exports(self.db_path, self.export_dir)
            self._record(
                STAGE_EXPORT_VALIDATE.stage_id,
                "ok" if ev.passed else "failed",
                time.perf_counter() - t0,
                "; ".join(ev.errors) if ev.errors else "",
            )
            export_val_summary = {
                "passed": ev.passed,
                "partial": ev.partial,
                "files": ev.files_validated,
                "errors": ev.errors,
            }
            if not ev.passed:
                return self._finalize(
                    started,
                    "failed",
                    row_counts=row_counts,
                    dq=dq_summary,
                    export_validation=export_val_summary,
                    failure={"stage": STAGE_EXPORT_VALIDATE.stage_id, "errors": ev.errors},
                )
            print(f"OK {STAGE_EXPORT_VALIDATE.stage_id}")

        status = "success"
        return self._finalize(
            started,
            status,
            row_counts=row_counts,
            dq=dq_summary,
            export_validation=export_val_summary,
        )

    def _finalize(
        self,
        started: datetime,
        status: str,
        *,
        row_counts: dict[str, Any] | None = None,
        dq: dict[str, Any] | None = None,
        export_validation: dict[str, Any] | None = None,
        failure: dict[str, Any] | None = None,
    ) -> PipelineRunResult:
        ended = datetime.now(timezone.utc)
        result = PipelineRunResult(
            run_id=self.run_id,
            started_at=started.isoformat(),
            ended_at=ended.isoformat(),
            status=status,
            database_path=str(self.db_path),
            as_of_date=self.as_of_date,
            geography_mode=self.geography_mode.value,
            export_dir=str(self.export_dir),
            dry_run=self.dry_run,
            stages=self.stages,
            row_counts=row_counts or {},
            dq=dq or {},
            export_validation=export_validation or {},
            failure=failure,
        )
        self.report_dir.mkdir(parents=True, exist_ok=True)
        report_path = self.report_dir / f"{self.run_id}.json"
        payload = asdict(result)
        payload["stages"] = [asdict(s) for s in self.stages]
        report_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"Report written: {report_path}")
        return result
