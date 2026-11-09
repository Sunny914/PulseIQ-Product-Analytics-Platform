"""Database path safety: block accidental writes to the authoritative DuckDB file."""

from __future__ import annotations

import os
from pathlib import Path

from db_config import DB_FILENAME, get_repo_root

_ALLOW_ENV = "PULSEIQ_ALLOW_AUTHORITATIVE_DB"
_ALLOW_CLI_FLAG = "allow_authoritative_db"


def authoritative_db_path() -> Path:
    return (get_repo_root() / DB_FILENAME).resolve()


def is_authoritative_path(path: Path) -> bool:
    try:
        return path.resolve() == authoritative_db_path()
    except OSError:
        return False


def resolve_pipeline_db_path(
    *,
    cli_db_path: Path | None,
    require_explicit: bool = True,
    allow_authoritative: bool = False,
) -> Path:
    """
    Resolve the target database path for pipeline runs.

    Requires --db-path or PULSEIQ_DB_PATH when require_explicit is True.
    """
    raw = None
    if cli_db_path is not None:
        raw = cli_db_path
    else:
        env = os.environ.get("PULSEIQ_DB_PATH")
        if env:
            raw = Path(env)

    if raw is None:
        if require_explicit:
            raise ValueError(
                "Database path is required. Pass --db-path or set PULSEIQ_DB_PATH "
                "to a non-authoritative DuckDB file."
            )
        raw = authoritative_db_path()

    resolved = raw.expanduser().resolve()

    env_allow = os.environ.get(_ALLOW_ENV, "").strip() in ("1", "true", "yes")
    if is_authoritative_path(resolved) and not (allow_authoritative or env_allow):
        raise ValueError(
            f"Refusing to modify authoritative database: {resolved}. "
            f"Use a different --db-path or set {_ALLOW_ENV}=1 with explicit intent."
        )

    parent = resolved.parent
    if not parent.exists():
        parent.mkdir(parents=True, exist_ok=True)

    return resolved
