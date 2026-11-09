"""
Account and user retention (exact-day D7 / D14) with cohort maturity.
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
CREATE OR REPLACE TABLE gold_fact_retention_cohort AS

WITH contexts AS (
    SELECT 'FULL_DATASET' AS ReportContext
    UNION ALL SELECT 'AS_OF'
),

account_cohorts AS (
    SELECT c.ReportContext, 'ACCOUNT' AS EntityType, 'OFFICIAL' AS AttributionPopulation,
           a.AccountId AS EntityId, CAST(a.CreatedDate AS DATE) AS CohortAnchorDate
    FROM gold_dim_accounts a
    CROSS JOIN contexts c
    WHERE (
        c.ReportContext = 'FULL_DATASET'
        OR CAST(a.CreatedDate AS DATE) <= {REPORT_AS_OF}
    )
),

user_cohorts AS (
    SELECT c.ReportContext, 'USER' AS EntityType, 'OFFICIAL' AS AttributionPopulation,
           u.UserId AS EntityId, CAST(u.CreatedDate AS DATE) AS CohortAnchorDate
    FROM gold_dim_users u
    CROSS JOIN contexts c
    WHERE (
        c.ReportContext = 'FULL_DATASET'
        OR CAST(u.CreatedDate AS DATE) <= {REPORT_AS_OF}
    )
),

cohorts AS (
    SELECT * FROM account_cohorts
    UNION ALL
    SELECT * FROM user_cohorts
),

windows AS (
    SELECT 'D7' AS RetentionWindow, 7 AS WindowDays
    UNION ALL SELECT 'D14', 14
),

metrics AS (
    SELECT
        co.ReportContext,
        co.EntityType,
        co.AttributionPopulation,
        w.RetentionWindow,
        w.WindowDays,
        COUNT(*) FILTER (
            WHERE co.CohortAnchorDate + w.WindowDays * INTERVAL 1 DAY <=
                CASE WHEN co.ReportContext = 'AS_OF' THEN {REPORT_AS_OF} ELSE DATE '2099-12-31' END
        ) AS EligibleEntities,
        COUNT(*) FILTER (
            WHERE co.CohortAnchorDate + w.WindowDays * INTERVAL 1 DAY <=
                CASE WHEN co.ReportContext = 'AS_OF' THEN {REPORT_AS_OF} ELSE DATE '2099-12-31' END
            AND (
                (co.EntityType = 'ACCOUNT' AND EXISTS (
                    SELECT 1 FROM gold_fact_qualified_product_events q
                    WHERE q.IsOfficialAccountQualified
                      AND q.AccountId = co.EntityId
                      AND q.EventDate = co.CohortAnchorDate + w.WindowDays * INTERVAL 1 DAY
                      AND (
                          co.ReportContext = 'FULL_DATASET'
                          OR (q.EventDate <= {REPORT_AS_OF} AND q.AccountCreatedDate <= {REPORT_AS_OF})
                      )
                ))
                OR
                (co.EntityType = 'USER' AND EXISTS (
                    SELECT 1 FROM gold_fact_qualified_product_events q
                    WHERE q.IsOfficialUserQualified
                      AND q.UserId = co.EntityId
                      AND q.EventDate = co.CohortAnchorDate + w.WindowDays * INTERVAL 1 DAY
                      AND (
                          co.ReportContext = 'FULL_DATASET'
                          OR (q.EventDate <= {REPORT_AS_OF} AND q.UserCreatedDate <= {REPORT_AS_OF})
                      )
                ))
            )
        ) AS RetainedEntities
    FROM cohorts co
    CROSS JOIN windows w
    GROUP BY 1, 2, 3, 4, 5
)

SELECT
    ReportContext,
    {REPORT_AS_OF} AS ReportAsOfDate,
    EntityType,
    AttributionPopulation,
    RetentionWindow,
    WindowDays,
    EligibleEntities,
    RetainedEntities,
    CASE WHEN EligibleEntities > 0
         THEN CAST(RetainedEntities AS DOUBLE) / EligibleEntities
         ELSE NULL END AS RetentionRate,
    'EXACT_CALENDAR_DAY' AS RetentionInterpretation
FROM metrics
ORDER BY ReportContext, EntityType, RetentionWindow
"""
)

print("✅ Created gold_fact_retention_cohort")
con.close()
