import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from as_of_date_sql import duckdb_date_literal
from db_config import connect_duckdb, get_as_of_date

AS_OF = duckdb_date_literal(get_as_of_date())

con = connect_duckdb()

con.execute(f"""
CREATE OR REPLACE TABLE silver_users AS
SELECT

    u.user_id,
    u.account_id,

    -- Core descriptors
    u.full_name,
    LOWER(
        SPLIT_PART(u.email, '@', 2)
    ) AS email_domain,

    u.job_role,
    u.user_status,

    -- Dates
    u.created_at,
    CAST(u.created_at AS DATE)
        AS created_date,

    u.last_seen_at,

    (CAST(u.created_at AS DATE) > {AS_OF}) AS is_future_created,

    -- User tenure: days since user creation (not account creation)
    CASE
        WHEN CAST(u.created_at AS DATE) > {AS_OF}
            THEN NULL
        ELSE DATE_DIFF(
            'day',
            CAST(u.created_at AS DATE),
            {AS_OF}
        )
    END AS user_tenure_days,

    -- Account tenure: days since linked account creation
    CASE
        WHEN a.account_id IS NULL
            THEN NULL
        WHEN CAST(a.created_at AS DATE) > {AS_OF}
            THEN NULL
        ELSE DATE_DIFF(
            'day',
            CAST(a.created_at AS DATE),
            {AS_OF}
        )
    END AS account_tenure_days,

    CASE
        WHEN u.last_seen_at IS NULL
            THEN NULL
        WHEN CAST(u.last_seen_at AS DATE) > {AS_OF}
            THEN NULL
        ELSE DATE_DIFF(
            'day',
            CAST(u.last_seen_at AS DATE),
            {AS_OF}
        )
    END AS days_since_last_seen,

    CASE
        WHEN u.last_seen_at IS NULL
            THEN NULL
        WHEN CAST(u.last_seen_at AS DATE) > {AS_OF}
            THEN 'future_last_seen'
        WHEN DATE_DIFF(
            'day',
            CAST(u.last_seen_at AS DATE),
            {AS_OF}
        ) < 0
            THEN NULL
        WHEN DATE_DIFF(
            'day',
            CAST(u.last_seen_at AS DATE),
            {AS_OF}
        ) < 7
            THEN '<7 days'
        WHEN DATE_DIFF(
            'day',
            CAST(u.last_seen_at AS DATE),
            {AS_OF}
        ) < 30
            THEN '7-29 days'
        WHEN DATE_DIFF(
            'day',
            CAST(u.last_seen_at AS DATE),
            {AS_OF}
        ) < 90
            THEN '30-89 days'
        ELSE '90+ days'
    END AS recency_bucket,

    -- Flags
    (u.user_status = 'active')
        AS is_active_user,

    u.is_admin

FROM bronze_users u
LEFT JOIN bronze_accounts a
    ON u.account_id = a.account_id
""")

print("✅ Created silver_users")

con.close()
