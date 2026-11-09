"""
Gold periodic engagement with WS-13 chronology-corrected qualified events.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from as_of_date_sql import duckdb_date_literal
from db_config import connect_duckdb, get_as_of_date

REPORT_AS_OF = duckdb_date_literal(get_as_of_date())

con = connect_duckdb()

con.execute(
    f"""
CREATE OR REPLACE TABLE gold_fact_engagement_periodic AS

WITH user_official AS (
    SELECT UserId AS EntityId, EventDate
    FROM gold_fact_qualified_product_events
    WHERE IsOfficialUserQualified
),
user_sensitivity AS (
    SELECT UserId AS EntityId, EventDate
    FROM gold_fact_qualified_product_events
    WHERE IsUserSensitivityQualified
),
account_official AS (
    SELECT AccountId AS EntityId, EventDate
    FROM gold_fact_qualified_product_events
    WHERE IsOfficialAccountQualified
),
account_sensitivity AS (
    SELECT AccountIdResolved AS EntityId, EventDate
    FROM gold_fact_qualified_product_events
    WHERE IsAccountSensitivityQualified
),

expanded AS (
    SELECT 'USER' AS EntityType, 'OFFICIAL' AS AttributionPopulation, EntityId, EventDate FROM user_official
    UNION ALL SELECT 'USER', 'SENSITIVITY', EntityId, EventDate FROM user_sensitivity
    UNION ALL SELECT 'ACCOUNT', 'OFFICIAL', EntityId, EventDate FROM account_official
    UNION ALL SELECT 'ACCOUNT', 'SENSITIVITY', EntityId, EventDate FROM account_sensitivity
),

with_context AS (
    SELECT 'FULL_DATASET' AS ReportContext, * FROM expanded
    UNION ALL
    SELECT 'AS_OF', e.*
    FROM expanded e
    WHERE e.EventDate <= {REPORT_AS_OF}
      AND (
          (e.EntityType = 'USER' AND e.EntityId IN (
              SELECT UserId FROM gold_dim_users
              WHERE CAST(CreatedDate AS DATE) <= {REPORT_AS_OF}
          ))
          OR
          (e.EntityType = 'ACCOUNT' AND e.EntityId IN (
              SELECT AccountId FROM gold_dim_accounts
              WHERE CAST(CreatedDate AS DATE) <= {REPORT_AS_OF}
          ))
      )
),

daily AS (
    SELECT ReportContext, 'DAY' AS PeriodType,
           EventDate AS PeriodStartDate, EventDate AS PeriodEndDate,
           EntityType, AttributionPopulation,
           COUNT(DISTINCT EntityId) AS ActiveEntityCount, COUNT(*) AS QualifiedEventCount
    FROM with_context GROUP BY 1,2,3,4,5,6
),
weekly AS (
    SELECT ReportContext, 'WEEK' AS PeriodType,
           CAST(DATE_TRUNC('week', EventDate) AS DATE) AS PeriodStartDate,
           CAST(DATE_TRUNC('week', EventDate) AS DATE) + INTERVAL 6 DAY AS PeriodEndDate,
           EntityType, AttributionPopulation,
           COUNT(DISTINCT EntityId) AS ActiveEntityCount, COUNT(*) AS QualifiedEventCount
    FROM with_context GROUP BY 1,2,3,4,5,6
),
monthly AS (
    SELECT ReportContext, 'MONTH' AS PeriodType,
           CAST(DATE_TRUNC('month', EventDate) AS DATE) AS PeriodStartDate,
           CAST(DATE_TRUNC('month', EventDate) AS DATE) + INTERVAL 1 MONTH - INTERVAL 1 DAY AS PeriodEndDate,
           EntityType, AttributionPopulation,
           COUNT(DISTINCT EntityId) AS ActiveEntityCount, COUNT(*) AS QualifiedEventCount
    FROM with_context GROUP BY 1,2,3,4,5,6
),
combined AS (
    SELECT * FROM daily UNION ALL SELECT * FROM weekly UNION ALL SELECT * FROM monthly
),
caps AS (
    SELECT
        (SELECT COUNT(*) FROM gold_dim_users) AS users_full,
        (SELECT COUNT(*) FROM gold_dim_users WHERE CAST(CreatedDate AS DATE) <= {REPORT_AS_OF}) AS users_asof,
        (SELECT COUNT(*) FROM gold_dim_accounts) AS accounts_full,
        (SELECT COUNT(*) FROM gold_dim_accounts WHERE CAST(CreatedDate AS DATE) <= {REPORT_AS_OF}) AS accounts_asof
)

SELECT
    c.ReportContext,
    {REPORT_AS_OF} AS ReportAsOfDate,
    c.PeriodType, c.PeriodStartDate, c.PeriodEndDate,
    c.EntityType, c.AttributionPopulation,
    c.ActiveEntityCount, c.QualifiedEventCount,
    CASE
        WHEN c.EntityType = 'USER' AND c.ReportContext = 'FULL_DATASET' THEN caps.users_full
        WHEN c.EntityType = 'USER' AND c.ReportContext = 'AS_OF' THEN caps.users_asof
        WHEN c.EntityType = 'ACCOUNT' AND c.ReportContext = 'FULL_DATASET' THEN caps.accounts_full
        ELSE caps.accounts_asof
    END AS EligibleEntityPopulationCap
FROM combined c
CROSS JOIN caps
ORDER BY ReportContext, PeriodType, PeriodStartDate, EntityType, AttributionPopulation
"""
)

print("✅ Created gold_fact_engagement_periodic")
con.close()
