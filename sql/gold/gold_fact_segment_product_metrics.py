import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from as_of_date_sql import duckdb_date_literal
from db_config import connect_duckdb, get_as_of_date

REPORT_AS_OF = duckdb_date_literal(get_as_of_date())

con = connect_duckdb()

con.execute(
    f"""
CREATE OR REPLACE TABLE gold_fact_segment_product_metrics AS

WITH contexts AS (
    SELECT 'FULL_DATASET' AS ReportContext
    UNION ALL SELECT 'AS_OF'
),

eligible AS (
    SELECT c.ReportContext, a.AccountId, a.Segment
    FROM gold_dim_accounts a
    CROSS JOIN contexts c
    WHERE c.ReportContext = 'FULL_DATASET'
       OR CAST(a.CreatedDate AS DATE) <= {REPORT_AS_OF}
),

active AS (
    SELECT c.ReportContext, q.AccountId
    FROM gold_fact_qualified_product_events q
    CROSS JOIN contexts c
    WHERE q.IsOfficialAccountQualified
      AND (c.ReportContext = 'FULL_DATASET'
           OR (q.EventDate <= {REPORT_AS_OF} AND q.AccountCreatedDate <= {REPORT_AS_OF}))
    GROUP BY 1, 2
),

breadth AS (
    SELECT ReportContext, AccountId, DistinctFeatureCount
    FROM gold_fact_feature_breadth_account
    WHERE AttributionPopulation = 'OFFICIAL'
),

activation AS (
    SELECT act.AccountId, act.IsActivated, act.TimeToValueDays, seg.Segment
    FROM gold_fact_advanced_activation act
    INNER JOIN gold_dim_accounts seg ON act.AccountId = seg.AccountId
)

SELECT
    e.ReportContext,
    {REPORT_AS_OF} AS ReportAsOfDate,
    e.Segment,
    COUNT(DISTINCT e.AccountId) AS EligibleAccounts,
    COUNT(DISTINCT ac.AccountId) AS ActiveAccounts,
    AVG(b.DistinctFeatureCount) AS AvgFeatureBreadth,
    SUM(CASE WHEN act.IsActivated THEN 1 ELSE 0 END) AS ActivatedAccounts,
    AVG(act.TimeToValueDays) FILTER (WHERE act.IsActivated) AS AvgTTVDaysActivated,
    'OFFICIAL' AS AttributionPopulation
FROM eligible e
LEFT JOIN active ac ON e.ReportContext = ac.ReportContext AND e.AccountId = ac.AccountId
LEFT JOIN breadth b ON e.ReportContext = b.ReportContext AND e.AccountId = b.AccountId
LEFT JOIN activation act ON e.AccountId = act.AccountId
GROUP BY e.ReportContext, e.Segment
ORDER BY e.ReportContext, e.Segment
"""
)

print("✅ Created gold_fact_segment_product_metrics")
con.close()
