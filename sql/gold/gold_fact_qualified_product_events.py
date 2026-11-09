"""
Qualified product events with chronology flags for WS-12/WS-13 analytics.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from as_of_date_sql import duckdb_date_literal
from db_config import connect_duckdb, get_as_of_date
from product_analytics_sql import (
    ACCOUNT_OFFICIAL_PREDICATE,
    ACCOUNT_SENSITIVITY_PREDICATE,
    USER_OFFICIAL_PREDICATE,
    USER_SENSITIVITY_PREDICATE,
)

REPORT_AS_OF = duckdb_date_literal(get_as_of_date())

con = connect_duckdb()

con.execute(
    f"""
CREATE OR REPLACE TABLE gold_fact_qualified_product_events AS
SELECT
    e.*,
    {REPORT_AS_OF} AS ReportAsOfDate,
    CAST(a.CreatedDate AS DATE) AS AccountCreatedDate,
    CAST(u.CreatedDate AS DATE) AS UserCreatedDate,
    CASE
        WHEN e.AccountId IS NULL THEN 'UNKNOWN'
        WHEN a.AccountId IS NULL THEN 'UNKNOWN'
        WHEN e.EventDate < CAST(a.CreatedDate AS DATE) THEN 'PRE_CREATION_EVENT'
        WHEN CAST(a.CreatedDate AS DATE) > {REPORT_AS_OF} THEN 'FUTURE_ENTITY_AS_OF'
        ELSE 'VALID'
    END AS AccountChronologyClass,
    CASE
        WHEN e.UserId IS NULL THEN 'UNKNOWN'
        WHEN u.UserId IS NULL THEN 'UNKNOWN'
        WHEN e.EventDate < CAST(u.CreatedDate AS DATE) THEN 'PRE_CREATION_EVENT'
        WHEN CAST(u.CreatedDate AS DATE) > {REPORT_AS_OF} THEN 'FUTURE_ENTITY_AS_OF'
        ELSE 'VALID'
    END AS UserChronologyClass,
    (
        {ACCOUNT_OFFICIAL_PREDICATE}
        AND a.AccountId IS NOT NULL
        AND e.EventDate >= CAST(a.CreatedDate AS DATE)
    ) AS IsOfficialAccountQualified,
    (
        {ACCOUNT_SENSITIVITY_PREDICATE}
        AND ar.AccountId IS NOT NULL
        AND e.EventDate >= CAST(ar.CreatedDate AS DATE)
    ) AS IsAccountSensitivityQualified,
    (
        {USER_OFFICIAL_PREDICATE}
        AND u.UserId IS NOT NULL
        AND e.EventDate >= CAST(u.CreatedDate AS DATE)
    ) AS IsOfficialUserQualified,
    (
        {USER_SENSITIVITY_PREDICATE}
        AND u.UserId IS NOT NULL
        AND e.EventDate >= CAST(u.CreatedDate AS DATE)
    ) AS IsUserSensitivityQualified
FROM gold_fact_product_events e
LEFT JOIN gold_dim_accounts a ON e.AccountId = a.AccountId
LEFT JOIN gold_dim_accounts ar ON e.AccountIdResolved = ar.AccountId
LEFT JOIN gold_dim_users u ON e.UserId = u.UserId
"""
)

print("✅ Created gold_fact_qualified_product_events")
con.close()
