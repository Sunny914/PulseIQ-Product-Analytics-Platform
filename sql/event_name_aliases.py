"""
Explicit event name alias map for Silver normalization (WS-4).

Only documented semantic/casing aliases belong here. Unknown names pass through unchanged.
See docs/event_taxonomy.md for rationale.
"""

from __future__ import annotations

# raw event_name -> canonical event_name_normalized
EVENT_NAME_ALIASES: dict[str, str] = {
    "ViewDashboard": "view_dashboard",
    "Login": "login",
    "user_login": "login",
}


def event_name_normalized_sql(source_column: str = "event_name") -> str:
    """Build a SQL CASE expression mapping aliases; preserve unmapped names."""
    when_clauses = "\n".join(
        f"        WHEN {source_column} = '{raw_name}' THEN '{canonical}'"
        for raw_name, canonical in EVENT_NAME_ALIASES.items()
    )
    return f"""CASE
{when_clauses}
        ELSE {source_column}
    END"""
