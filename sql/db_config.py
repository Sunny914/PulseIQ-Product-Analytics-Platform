"""
Central DuckDB configuration for PulseIQ transformation scripts.

Resolves paths from this file's location (not the process working directory).
"""

from __future__ import annotations

import os
import re
from datetime import date, datetime
from pathlib import Path

import duckdb

# sql/db_config.py -> repository root
REPO_ROOT: Path = Path(__file__).resolve().parent.parent

DB_FILENAME = "product_analytics_light.db"

DEFAULT_AS_OF_DATE = date(2026, 7, 11)
_AS_OF_DATE_ENV = "PULSEIQ_AS_OF_DATE"
_ISO_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def get_repo_root() -> Path:
    """Return the PulseIQ repository root directory."""
    return REPO_ROOT


def get_db_path() -> Path:
    """
    Return the authoritative DuckDB file path.

    Override with the PULSEIQ_DB_PATH environment variable when needed.
    """
    override = os.environ.get("PULSEIQ_DB_PATH")
    if override:
        return Path(override).expanduser().resolve()
    return REPO_ROOT / DB_FILENAME


def get_as_of_date() -> date:
    """
    Reporting reference date for age, tenure, and recency calculations.

    Override with PULSEIQ_AS_OF_DATE (ISO YYYY-MM-DD). Defaults to 2026-07-11
    (historical baseline implied by last materialized Silver ages).
    """
    raw = os.environ.get(_AS_OF_DATE_ENV)
    if raw is None or raw.strip() == "":
        return DEFAULT_AS_OF_DATE

    value = raw.strip()
    if not _ISO_DATE_PATTERN.match(value):
        raise ValueError(
            f"{_AS_OF_DATE_ENV} must be ISO YYYY-MM-DD; got {value!r}"
        )

    try:
        parsed = datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError(
            f"{_AS_OF_DATE_ENV} is not a valid calendar date: {value!r}"
        ) from exc

    return parsed


def connect_duckdb(*, read_only: bool = False) -> duckdb.DuckDBPyConnection:
    """Open a connection to the authoritative PulseIQ DuckDB database."""
    path = str(get_db_path())
    if read_only:
        return duckdb.connect(path, read_only=True)
    return duckdb.connect(path)
