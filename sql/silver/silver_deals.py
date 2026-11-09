import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from as_of_date_sql import duckdb_date_literal
from db_config import connect_duckdb, get_as_of_date

AS_OF = duckdb_date_literal(get_as_of_date())

con = connect_duckdb()


con.execute(f"""
CREATE OR REPLACE TABLE silver_deals AS
SELECT

    deal_id,
    account_id,
    owner_user_id,
    pipeline_id,
    current_stage_id,

    LOWER(status) AS status,

    created_at,
    CAST(created_at AS DATE) AS created_date,

    closed_at,
    CAST(closed_at AS DATE) AS closed_date,

    last_stage_changed_at,
    CAST(last_stage_changed_at AS DATE)
        AS last_stage_changed_date,

    amount,
    UPPER(currency) AS currency,
    UPPER(country_code) AS country_code,

    source_system,

    (closed_at IS NOT NULL) AS is_closed,

    CASE
        WHEN LOWER(status)
             IN ('won','closed_won')
        THEN TRUE
        ELSE FALSE
    END AS is_won,

    (CAST(created_at AS DATE) > {AS_OF}) AS is_future_created,

    CASE
        WHEN closed_at IS NOT NULL
        THEN DATE_DIFF(
            'day',
            CAST(created_at AS DATE),
            CAST(closed_at AS DATE)
        )
        ELSE NULL
    END AS deal_cycle_days,

    -- Open pipeline age only (NULL when closed or future-created)
    CASE
        WHEN CAST(created_at AS DATE) > {AS_OF}
            THEN NULL
        WHEN closed_at IS NOT NULL
            THEN NULL
        ELSE DATE_DIFF(
            'day',
            CAST(created_at AS DATE),
            {AS_OF}
        )
    END AS deal_age_days

FROM bronze_deals
""")

print("✅ Created silver_deals")

con.close()
