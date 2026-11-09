import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from as_of_date_sql import duckdb_date_literal
from db_config import connect_duckdb, get_as_of_date

REPORT_AS_OF = duckdb_date_literal(get_as_of_date())

con = connect_duckdb()

con.execute(
    f"""
CREATE OR REPLACE TABLE gold_fact_product_activity_recency_account AS
WITH contexts AS (
    SELECT 'FULL_DATASET' AS ReportContext
    UNION ALL SELECT 'AS_OF'
),
agg AS (
    SELECT c.ReportContext, b.AccountId,
           MIN(b.EventDate) AS FirstActivityDate,
           MAX(b.EventDate) AS LastActivityDate,
           COUNT(*) AS QualifiedEventCount
    FROM gold_fact_qualified_product_events b
    CROSS JOIN contexts c
    WHERE b.IsOfficialAccountQualified
      AND (c.ReportContext = 'FULL_DATASET'
           OR (b.EventDate <= {REPORT_AS_OF} AND b.AccountCreatedDate <= {REPORT_AS_OF}))
    GROUP BY 1, 2
),
with_dims AS (
    SELECT a.*, d.Segment AS AccountSegment,
           CAST(d.CreatedDate AS DATE) AS AccountCreatedDate,
           (CAST(d.CreatedDate AS DATE) > {REPORT_AS_OF}) AS IsFutureCreatedAccount
    FROM agg a
    INNER JOIN gold_dim_accounts d ON a.AccountId = d.AccountId
)
SELECT ReportContext, {REPORT_AS_OF} AS ReportAsOfDate, 'OFFICIAL' AS AttributionPopulation,
       AccountId, AccountSegment, AccountCreatedDate, IsFutureCreatedAccount,
       FirstActivityDate, LastActivityDate, QualifiedEventCount,
       CASE WHEN ReportContext = 'AS_OF'
            THEN DATE_DIFF('day', LastActivityDate, {REPORT_AS_OF}) ELSE NULL END AS DaysSinceLastActivity,
       CASE
         WHEN ReportContext = 'AS_OF' AND DATE_DIFF('day', LastActivityDate, {REPORT_AS_OF}) BETWEEN 0 AND 6
              THEN 'active_0_6_days'
         WHEN ReportContext = 'AS_OF' AND DATE_DIFF('day', LastActivityDate, {REPORT_AS_OF}) BETWEEN 7 AND 29
              THEN 'active_7_29_days'
         WHEN ReportContext = 'AS_OF' AND DATE_DIFF('day', LastActivityDate, {REPORT_AS_OF}) BETWEEN 30 AND 89
              THEN 'active_30_89_days'
         WHEN ReportContext = 'AS_OF' AND DATE_DIFF('day', LastActivityDate, {REPORT_AS_OF}) >= 90
              THEN 'active_90_plus_days'
         WHEN ReportContext = 'FULL_DATASET' THEN 'full_dataset_last_event'
         ELSE 'other'
       END AS ActivityRecencyBucket
FROM with_dims
"""
)

con.execute(
    f"""
CREATE OR REPLACE TABLE gold_fact_product_activity_recency_user AS
WITH contexts AS (
    SELECT 'FULL_DATASET' AS ReportContext
    UNION ALL SELECT 'AS_OF'
),
agg AS (
    SELECT c.ReportContext, b.UserId,
           MIN(b.EventDate) AS FirstActivityDate,
           MAX(b.EventDate) AS LastActivityDate,
           COUNT(*) AS QualifiedEventCount
    FROM gold_fact_qualified_product_events b
    CROSS JOIN contexts c
    WHERE b.IsOfficialUserQualified
      AND (c.ReportContext = 'FULL_DATASET'
           OR (b.EventDate <= {REPORT_AS_OF} AND b.UserCreatedDate <= {REPORT_AS_OF}))
    GROUP BY 1, 2
),
with_dims AS (
    SELECT a.*, CAST(u.CreatedDate AS DATE) AS UserCreatedDate,
           (CAST(u.CreatedDate AS DATE) > {REPORT_AS_OF}) AS IsFutureCreatedUser
    FROM agg a
    INNER JOIN gold_dim_users u ON a.UserId = u.UserId
)
SELECT ReportContext, {REPORT_AS_OF} AS ReportAsOfDate, 'OFFICIAL' AS AttributionPopulation,
       UserId, UserCreatedDate, IsFutureCreatedUser,
       FirstActivityDate, LastActivityDate, QualifiedEventCount,
       CASE WHEN ReportContext = 'AS_OF'
            THEN DATE_DIFF('day', LastActivityDate, {REPORT_AS_OF}) ELSE NULL END AS DaysSinceLastActivity,
       CASE
         WHEN ReportContext = 'AS_OF' AND DATE_DIFF('day', LastActivityDate, {REPORT_AS_OF}) BETWEEN 0 AND 6
              THEN 'active_0_6_days'
         WHEN ReportContext = 'AS_OF' AND DATE_DIFF('day', LastActivityDate, {REPORT_AS_OF}) BETWEEN 7 AND 29
              THEN 'active_7_29_days'
         WHEN ReportContext = 'AS_OF' AND DATE_DIFF('day', LastActivityDate, {REPORT_AS_OF}) BETWEEN 30 AND 89
              THEN 'active_30_89_days'
         WHEN ReportContext = 'AS_OF' AND DATE_DIFF('day', LastActivityDate, {REPORT_AS_OF}) >= 90
              THEN 'active_90_plus_days'
         WHEN ReportContext = 'FULL_DATASET' THEN 'full_dataset_last_event'
         ELSE 'other'
       END AS ActivityRecencyBucket
FROM with_dims
"""
)

print("✅ Created gold_fact_product_activity_recency_account and user")
con.close()
