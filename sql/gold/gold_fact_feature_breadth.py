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
CREATE OR REPLACE TABLE gold_fact_feature_breadth_account AS
WITH contexts AS (SELECT 'FULL_DATASET' AS ReportContext UNION ALL SELECT 'AS_OF'),
events AS (
    SELECT c.ReportContext, b.AccountId, a.Segment AS AccountSegment, b.FeatureName, b.EventDate
    FROM gold_fact_qualified_product_events b
    CROSS JOIN contexts c
    INNER JOIN gold_dim_accounts a ON b.AccountId = a.AccountId
    WHERE {feature_is_valid_sql("b.FeatureName")} AND b.IsOfficialAccountQualified
      AND (c.ReportContext = 'FULL_DATASET'
           OR (b.EventDate <= {REPORT_AS_OF} AND b.AccountCreatedDate <= {REPORT_AS_OF}))
),
per_account AS (
    SELECT ReportContext, AccountId, AccountSegment,
           COUNT(DISTINCT FeatureName) AS DistinctFeatureCount,
           COUNT(*) AS QualifiedFeatureEventCount,
           MIN(EventDate) AS FirstFeatureActivityDate,
           MAX(EventDate) AS LastFeatureActivityDate
    FROM events GROUP BY 1,2,3
)
SELECT ReportContext, {REPORT_AS_OF} AS ReportAsOfDate, 'OFFICIAL' AS AttributionPopulation,
       AccountId, AccountSegment, DistinctFeatureCount, QualifiedFeatureEventCount,
       FirstFeatureActivityDate, LastFeatureActivityDate,
       CASE WHEN DistinctFeatureCount = 1 THEN 'narrow_1_feature'
            WHEN DistinctFeatureCount = 2 THEN 'moderate_2_features'
            ELSE 'broad_3plus_features' END AS FeatureBreadthBucket
FROM per_account
"""
)

con.execute(
    f"""
CREATE OR REPLACE TABLE gold_fact_feature_breadth_user AS
WITH contexts AS (SELECT 'FULL_DATASET' AS ReportContext UNION ALL SELECT 'AS_OF'),
events AS (
    SELECT c.ReportContext, b.UserId, b.FeatureName, b.EventDate
    FROM gold_fact_qualified_product_events b
    CROSS JOIN contexts c
    WHERE {feature_is_valid_sql("b.FeatureName")} AND b.IsOfficialUserQualified
      AND (c.ReportContext = 'FULL_DATASET'
           OR (b.EventDate <= {REPORT_AS_OF} AND b.UserCreatedDate <= {REPORT_AS_OF}))
),
per_user AS (
    SELECT ReportContext, UserId,
           COUNT(DISTINCT FeatureName) AS DistinctFeatureCount,
           COUNT(*) AS QualifiedFeatureEventCount,
           MIN(EventDate) AS FirstFeatureActivityDate,
           MAX(EventDate) AS LastFeatureActivityDate
    FROM events GROUP BY 1,2
)
SELECT ReportContext, {REPORT_AS_OF} AS ReportAsOfDate, 'OFFICIAL' AS AttributionPopulation,
       UserId, DistinctFeatureCount, QualifiedFeatureEventCount,
       FirstFeatureActivityDate, LastFeatureActivityDate,
       CASE WHEN DistinctFeatureCount = 1 THEN 'narrow_1_feature'
            WHEN DistinctFeatureCount = 2 THEN 'moderate_2_features'
            ELSE 'broad_3plus_features' END AS FeatureBreadthBucket
FROM per_user
"""
)

print("✅ Created gold_fact_feature_breadth_account and gold_fact_feature_breadth_user")
con.close()
