import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from as_of_date_sql import duckdb_date_literal
from db_config import connect_duckdb, get_as_of_date
from product_analytics_sql import feature_is_valid_sql

REPORT_AS_OF = duckdb_date_literal(get_as_of_date())

con = connect_duckdb()

con.execute(
    f"""
CREATE OR REPLACE TABLE gold_fact_feature_adoption_by_period AS
WITH contexts AS (
    SELECT 'FULL_DATASET' AS ReportContext
    UNION ALL SELECT 'AS_OF'
),
qualified AS (
    SELECT q.*, c.ReportContext
    FROM gold_fact_qualified_product_events q
    CROSS JOIN contexts c
    WHERE {feature_is_valid_sql("q.FeatureName")}
      AND (
        c.ReportContext = 'FULL_DATASET'
        OR (q.EventDate <= {REPORT_AS_OF}
            AND COALESCE(q.AccountCreatedDate, q.UserCreatedDate) <= {REPORT_AS_OF})
      )
),
periods AS (
    SELECT 'MONTH' AS PeriodType,
           CAST(DATE_TRUNC('month', EventDate) AS DATE) AS PeriodStartDate,
           CAST(DATE_TRUNC('month', EventDate) AS DATE) + INTERVAL 1 MONTH - INTERVAL 1 DAY AS PeriodEndDate,
           ReportContext, 'USER' AS EntityType, UserId AS EntityId, FeatureName
    FROM qualified WHERE IsOfficialUserQualified
    UNION ALL
    SELECT 'MONTH',
           CAST(DATE_TRUNC('month', EventDate) AS DATE),
           CAST(DATE_TRUNC('month', EventDate) AS DATE) + INTERVAL 1 MONTH - INTERVAL 1 DAY,
           ReportContext, 'ACCOUNT', AccountId, FeatureName
    FROM qualified WHERE IsOfficialAccountQualified
)
SELECT ReportContext, {REPORT_AS_OF} AS ReportAsOfDate, PeriodType,
       PeriodStartDate, PeriodEndDate, EntityType, 'OFFICIAL' AS AttributionPopulation,
       FeatureName, COUNT(DISTINCT EntityId) AS AdoptedEntityCount, COUNT(*) AS FeatureEventCount
FROM periods
GROUP BY 1,2,3,4,5,6,7,8
"""
)

print("✅ Created gold_fact_feature_adoption_by_period")
con.close()
