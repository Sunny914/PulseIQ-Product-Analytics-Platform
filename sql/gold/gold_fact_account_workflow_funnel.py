"""
Descriptive account workflow funnel (non-causal). Chronology-valid official events only.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from as_of_date_sql import duckdb_date_literal
from db_config import connect_duckdb, get_as_of_date
from product_analytics_sql import FUNNEL_STAGES

REPORT_AS_OF = duckdb_date_literal(get_as_of_date())
STAGE_LIST = ", ".join(f"'{s}'" for s in FUNNEL_STAGES)

con = connect_duckdb()

con.execute(
    f"""
CREATE OR REPLACE TABLE gold_fact_account_workflow_funnel AS

WITH contexts AS (
    SELECT 'FULL_DATASET' AS ReportContext
    UNION ALL SELECT 'AS_OF'
),

eligible_accounts AS (
    SELECT c.ReportContext, a.AccountId
    FROM gold_dim_accounts a
    CROSS JOIN contexts c
    WHERE c.ReportContext = 'FULL_DATASET'
       OR CAST(a.CreatedDate AS DATE) <= {REPORT_AS_OF}
),

first_hits AS (
    SELECT c.ReportContext, q.AccountId, q.EventNameNormalized,
           MIN(q.EventTimestamp) AS FirstEventAt
    FROM gold_fact_qualified_product_events q
    CROSS JOIN contexts c
    WHERE q.IsOfficialAccountQualified
      AND q.EventNameNormalized IN ({STAGE_LIST})
      AND (c.ReportContext = 'FULL_DATASET'
           OR (q.EventDate <= {REPORT_AS_OF} AND q.AccountCreatedDate <= {REPORT_AS_OF}))
    GROUP BY 1, 2, 3
),

stage_flags AS (
    SELECT
        ea.ReportContext,
        ea.AccountId,
        MAX(CASE WHEN fh.EventNameNormalized = 'login' THEN 1 ELSE 0 END) AS ReachedLogin,
        MAX(CASE WHEN fh.EventNameNormalized = 'view_dashboard' THEN 1 ELSE 0 END) AS ReachedDashboard,
        MAX(CASE WHEN fh.EventNameNormalized = 'create_deal' THEN 1 ELSE 0 END) AS ReachedCreateDeal,
        MAX(CASE WHEN fh.EventNameNormalized = 'move_deal_stage' THEN 1 ELSE 0 END) AS ReachedMoveStage,
        MAX(CASE WHEN fh.EventNameNormalized = 'log_activity' THEN 1 ELSE 0 END) AS ReachedLogActivity
    FROM eligible_accounts ea
    LEFT JOIN first_hits fh
      ON ea.ReportContext = fh.ReportContext AND ea.AccountId = fh.AccountId
    GROUP BY 1, 2
),

stage_long AS (
    SELECT ReportContext, 1 AS StageOrder, 'login' AS FunnelStage,
           SUM(ReachedLogin) AS EntitiesReachedStage
    FROM stage_flags GROUP BY 1
    UNION ALL SELECT ReportContext, 2, 'view_dashboard', SUM(ReachedDashboard) FROM stage_flags GROUP BY 1
    UNION ALL SELECT ReportContext, 3, 'create_deal', SUM(ReachedCreateDeal) FROM stage_flags GROUP BY 1
    UNION ALL SELECT ReportContext, 4, 'move_deal_stage', SUM(ReachedMoveStage) FROM stage_flags GROUP BY 1
    UNION ALL SELECT ReportContext, 5, 'log_activity', SUM(ReachedLogActivity) FROM stage_flags GROUP BY 1
),

denoms AS (
    SELECT ReportContext, COUNT(*) AS EligibleAccounts
    FROM eligible_accounts
    GROUP BY 1
)

SELECT
    sl.ReportContext,
    {REPORT_AS_OF} AS ReportAsOfDate,
    'ACCOUNT' AS EntityType,
    'OFFICIAL' AS AttributionPopulation,
  sl.StageOrder,
  sl.FunnelStage,
  d.EligibleAccounts,
  sl.EntitiesReachedStage,
  CAST(sl.EntitiesReachedStage AS DOUBLE) / d.EligibleAccounts AS StageReachRate,
  'DESCRIPTIVE_NON_CAUSAL' AS FunnelInterpretation
FROM stage_long sl
INNER JOIN denoms d ON sl.ReportContext = d.ReportContext
ORDER BY sl.ReportContext, sl.StageOrder
"""
)

print("✅ Created gold_fact_account_workflow_funnel")
con.close()
