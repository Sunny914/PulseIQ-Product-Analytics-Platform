"""
Deterministic event_sk SQL fragments for silver_product_events.

See docs/event_identity.md for methodology.
"""

# Canonical immutable payload fields (excludes ingested_at and derived columns).
EVENT_PAYLOAD_CANONICAL_SQL = """
    concat_ws(
        '|',
        coalesce(event_name, ''),
        coalesce(user_id, ''),
        coalesce(account_id, ''),
        coalesce(deal_id, ''),
        coalesce(CAST(event_timestamp AS VARCHAR), ''),
        coalesce(event_properties, ''),
        coalesce(source_system, ''),
        coalesce(platform, ''),
        coalesce(device_type, ''),
        coalesce(app_version, ''),
        coalesce(country_code, '')
    )
"""

EVENT_PAYLOAD_DIGEST_SQL = f"sha256({EVENT_PAYLOAD_CANONICAL_SQL})"

EVENT_SK_EXPRESSION_SQL = f"""
    CASE
        WHEN event_id IS NOT NULL THEN 'SRC-' || event_id
        ELSE 'SYN-' || payload_digest
             || CASE
                    WHEN payload_occurrence > 1
                    THEN '-D' || CAST(payload_occurrence AS VARCHAR)
                    ELSE ''
                END
    END
"""
