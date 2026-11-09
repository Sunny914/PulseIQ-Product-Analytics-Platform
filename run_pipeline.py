#!/usr/bin/env python3
"""
PulseIQ Phase 0 end-to-end pipeline entry point (WS-10).

Raw validation → load → Bronze → Silver → Gold → CSV export → DQ validation.
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

# Repository root is this file's directory; sql modules live under sql/
REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT / "sql"))

from db_config import DEFAULT_AS_OF_DATE  # noqa: E402
from pipeline.geography import GeographyMode  # noqa: E402
from pipeline.runner import DEFAULT_EXPORT_DIR, PipelineRunner  # noqa: E402
from pipeline.safety import resolve_pipeline_db_path  # noqa: E402

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def parse_as_of_date(cli_value: str | None) -> str:
    """CLI --as-of-date overrides PULSEIQ_AS_OF_DATE; default 2026-07-11."""
    import os

    raw = cli_value
    if raw is None:
        raw = os.environ.get("PULSEIQ_AS_OF_DATE")
    if raw is None or raw.strip() == "":
        return DEFAULT_AS_OF_DATE.isoformat()
    value = raw.strip()
    if not _ISO_DATE.match(value):
        raise ValueError(f"--as-of-date must be ISO YYYY-MM-DD; got {value!r}")
    datetime.strptime(value, "%Y-%m-%d")
    return value


def parse_geography_mode(value: str) -> GeographyMode:
    try:
        return GeographyMode(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"geography-mode must be 'source' or 'derived-fixture'; got {value!r}"
        ) from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the PulseIQ analytics pipeline.")
    parser.add_argument(
        "--db-path",
        type=Path,
        default=None,
        help="Target DuckDB file (required unless PULSEIQ_DB_PATH is set).",
    )
    parser.add_argument(
        "--export-dir",
        type=Path,
        default=None,
        help=f"Gold CSV output directory (default: {DEFAULT_EXPORT_DIR}).",
    )
    parser.add_argument(
        "--as-of-date",
        type=str,
        default=None,
        help="Reporting date YYYY-MM-DD (overrides PULSEIQ_AS_OF_DATE).",
    )
    parser.add_argument(
        "--geography-mode",
        type=parse_geography_mode,
        default=GeographyMode.DERIVED_FIXTURE,
        help="source | derived-fixture",
    )
    parser.add_argument(
        "--snapshot-dir",
        type=Path,
        default=None,
        help="Raw snapshot directory (default: data/source_snapshot).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print execution order without modifying data.",
    )
    parser.add_argument(
        "--skip-dq",
        action="store_true",
        help="Skip pipeline DQ and export validation stages (developer pytest still recommended).",
    )
    parser.add_argument(
        "--allow-authoritative-db",
        action="store_true",
        help="Allow writes to product_analytics_light.db (discouraged).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    import os

    try:
        as_of = parse_as_of_date(args.as_of_date)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.dry_run and args.db_path is None and not os.environ.get("PULSEIQ_DB_PATH"):
        db_path = (REPO_ROOT / "artifacts" / "pulseiq.duckdb").resolve()
    else:
        try:
            db_path = resolve_pipeline_db_path(
                cli_db_path=args.db_path,
                require_explicit=True,
                allow_authoritative=args.allow_authoritative_db,
            )
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 2

    export_dir = (args.export_dir or DEFAULT_EXPORT_DIR).expanduser().resolve()

    runner = PipelineRunner(
        db_path,
        as_of_date=as_of,
        geography_mode=args.geography_mode,
        export_dir=export_dir,
        snapshot_dir=args.snapshot_dir,
        dry_run=args.dry_run,
        skip_dq=args.skip_dq,
    )
    result = runner.run()
    if result.status == "success":
        return 0
    if result.status == "dry_run":
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
