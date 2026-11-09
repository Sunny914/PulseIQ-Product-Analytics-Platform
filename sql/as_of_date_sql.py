"""
WS-7: Reporting reference date (`as_of_date`) for DuckDB SQL transformations.

Literals are generated only from validated Python `date` objects (see db_config.get_as_of_date).
"""

from __future__ import annotations

from datetime import date


def duckdb_date_literal(as_of: date) -> str:
    """Return a DuckDB DATE literal for embedding in SQL (validated ISO date only)."""
    return f"DATE '{as_of.isoformat()}'"
