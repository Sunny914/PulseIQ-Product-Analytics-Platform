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
CREATE OR REPLACE TABLE gold_fact_feature_adoption_account AS
WITH contexts AS (
    SELECT 'FULL_DATASET' AS ReportContext
    UNION ALL SELECT 'AS_OF'
),
base AS (
    SELECT q.*, c.ReportContext
    FROM gold_fact_qualified_product_events q
    CROSS JOIN contexts c
    WHERE {feature_is_valid_sql("q.FeatureName")}
      AND (
        c.ReportContext = 'FULL_DATASET'
        OR (q.EventDate <= {REPORT_AS_OF} AND q.AccountCreatedDate <= {REPORT_AS_OF})
      )
),
official AS (
    SELECT b.ReportContext, 'OFFICIAL' AS AttributionPopulation,
           b.AccountId, a.Segment AS AccountSegment, b.FeatureName,
           COUNT(*) AS FeatureEventCount,
           MIN(b.EventDate) AS FirstFeatureUseDate,
           MAX(b.EventDate) AS LastFeatureUseDate,
           (COUNT(*) > 1) AS IsRepeatFeatureUsage
    FROM base b
    INNER JOIN gold_dim_accounts a ON b.AccountId = a.AccountId
    WHERE b.IsOfficialAccountQualified
    GROUP BY 1,2,3,4,5
),
sensitivity AS (
    SELECT b.ReportContext, 'SENSITIVITY' AS AttributionPopulation,
           b.AccountIdResolved AS AccountId, a.Segment AS AccountSegment, b.FeatureName,
           COUNT(*) AS FeatureEventCount,
           MIN(b.EventDate) AS FirstFeatureUseDate,
           MAX(b.EventDate) AS LastFeatureUseDate,
           (COUNT(*) > 1) AS IsRepeatFeatureUsage
    FROM base b
    LEFT JOIN gold_dim_accounts a ON b.AccountIdResolved = a.AccountId
    WHERE b.IsAccountSensitivityQualified
    GROUP BY 1,2,3,4,5
)
SELECT ReportContext, {REPORT_AS_OF} AS ReportAsOfDate, AttributionPopulation,
       AccountId, AccountSegment, FeatureName, FeatureEventCount,
       FirstFeatureUseDate, LastFeatureUseDate, IsRepeatFeatureUsage, TRUE AS HasAdoptedFeature
FROM official
UNION ALL
SELECT ReportContext, {REPORT_AS_OF}, AttributionPopulation,
       AccountId, AccountSegment, FeatureName, FeatureEventCount,
       FirstFeatureUseDate, LastFeatureUseDate, IsRepeatFeatureUsage, TRUE
FROM sensitivity
"""
)

print("✅ Created gold_fact_feature_adoption_account")
con.close()
