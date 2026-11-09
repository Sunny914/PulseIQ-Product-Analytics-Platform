"""
WS-2 raw snapshot checks (requires pytest: pip install pytest).

Validates Parquet files against MANIFEST.json without modifying databases.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_snapshot_files_validate() -> None:
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "sql" / "validate_raw_snapshot.py")],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout


def test_load_raw_idempotent_on_temp_db(tmp_path: Path) -> None:
    db_path = tmp_path / "pulseiq_raw_test.duckdb"
    load_script = REPO_ROOT / "sql" / "load_raw.py"
    validate_script = REPO_ROOT / "sql" / "validate_raw_snapshot.py"

    for _ in range(2):
        proc = subprocess.run(
            [sys.executable, str(load_script), "--db-path", str(db_path)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == 0, proc.stderr or proc.stdout

    proc = subprocess.run(
        [sys.executable, str(validate_script), "--db-path", str(db_path)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
