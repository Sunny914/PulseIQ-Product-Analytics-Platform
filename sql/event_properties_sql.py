"""
WS-6: Parse product event_properties JSON once for Silver (Gold reads typed columns).
"""

from __future__ import annotations

# Requires column `event_properties` (VARCHAR JSON payload) in scope.
EVENT_PROPERTIES_JSON_EXPR = "TRY_CAST(event_properties AS JSON)"

EVENT_PROPERTIES_PARSE_STATUS_SQL = f"""
    CASE
        WHEN event_properties IS NULL THEN 'NULL_PAYLOAD'
        WHEN {EVENT_PROPERTIES_JSON_EXPR} IS NULL THEN 'INVALID_JSON'
        ELSE 'OK'
    END AS event_properties_parse_status
"""

EVENT_PROPERTIES_JSON_COLUMN_SQL = f"""
    CASE
        WHEN event_properties IS NULL THEN CAST(NULL AS JSON)
        ELSE {EVENT_PROPERTIES_JSON_EXPR}
    END AS event_properties_json
"""


def _extract_json_string(json_key: str, column_alias: str) -> str:
    return f"""
    CASE
        WHEN event_properties_parse_status = 'OK'
            THEN json_extract_string(event_properties_json, '$.{json_key}')
        ELSE NULL
    END AS {column_alias}
    """


EVENT_PROPERTIES_EXTRACT_COLUMNS_SQL = ",\n".join(
    [
        _extract_json_string("feature_name", "feature_name").strip(),
        _extract_json_string("source", "event_source").strip(),
        _extract_json_string("pipeline_id", "pipeline_id").strip(),
        _extract_json_string("stage_id", "stage_id").strip(),
    ]
)
