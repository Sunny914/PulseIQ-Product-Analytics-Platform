import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from as_of_date_sql import duckdb_date_literal
from db_config import connect_duckdb, get_as_of_date

REPORT_AS_OF = duckdb_date_literal(get_as_of_date())

con = connect_duckdb()

con.execute(f"""
CREATE OR REPLACE TABLE gold_fact_activation_as_of AS
SELECT

    a.AccountId,
    CAST(a.CreatedDate AS DATE) AS CreatedDate,
    {REPORT_AS_OF} AS ReportAsOfDate,
    CAST(a.CreatedDate AS DATE) + INTERVAL 14 DAY AS ActivationWindowEndDate,

    (CAST(a.CreatedDate AS DATE) > {REPORT_AS_OF}) AS IsFutureCreated,

    (
        CAST(a.CreatedDate AS DATE) + INTERVAL 14 DAY <= {REPORT_AS_OF}
    ) AS IsWindowCompleteAsOf,

    (
        CAST(a.CreatedDate AS DATE) <= {REPORT_AS_OF}
        AND CAST(a.CreatedDate AS DATE) + INTERVAL 14 DAY <= {REPORT_AS_OF}
    ) AS IsEligibleAsOf,

    act.IsActivated AS IsActivatedFullDataset,

    CASE
        WHEN CAST(a.CreatedDate AS DATE) <= {REPORT_AS_OF}
         AND CAST(a.CreatedDate AS DATE) + INTERVAL 14 DAY <= {REPORT_AS_OF}
         AND act.IsActivated
        THEN TRUE
        ELSE FALSE
    END AS IsActivatedAsOf,

    act.TimeToValueDays AS TimeToValueDaysFullDataset,

    CASE
        WHEN CAST(a.CreatedDate AS DATE) <= {REPORT_AS_OF}
         AND CAST(a.CreatedDate AS DATE) + INTERVAL 14 DAY <= {REPORT_AS_OF}
         AND act.IsActivated
        THEN act.TimeToValueDays
        ELSE NULL
    END AS TimeToValueDaysAsOf

FROM gold_dim_accounts a
INNER JOIN gold_fact_advanced_activation act
    ON a.AccountId = act.AccountId
ORDER BY a.AccountId
""")

print("✅ Created gold_fact_activation_as_of")

con.close()
