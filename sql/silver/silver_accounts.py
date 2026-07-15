import duckdb
import os

con = duckdb.connect(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "product_analytics_light.db"
    )
)

con.execute("""
CREATE OR REPLACE TABLE silver_accounts AS
SELECT

    a.account_id,

    -- Core descriptors
    TRIM(a.account_name)                    AS account_name,
    UPPER(a.country_code)                  AS country_code,
    a.industry,
    a.employee_band,
    UPPER(a.segment)                       AS segment,
    UPPER(a.acquisition_channel)           AS acquisition_channel,

    -- Geography attributes (account-level enrichment)
    g.country_name,
    g.region,
    g.market,
    g.sales_region,
    g.currency AS local_currency,

    -- Dates
    a.created_at,
    CAST(a.created_at AS DATE)             AS created_date,
    a.trial_start_date,
    a.trial_end_date,

    -- Age metrics
    CASE
        WHEN CAST(a.created_at AS DATE) > CURRENT_DATE THEN 0
        ELSE DATE_DIFF(
            'day',
            CAST(a.created_at AS DATE),
            CURRENT_DATE
        )
    END AS account_age_days,

    CASE
        WHEN CAST(a.created_at AS DATE) > CURRENT_DATE
            THEN 'future'

        WHEN DATE_DIFF(
                'day',
                CAST(a.created_at AS DATE),
                CURRENT_DATE
             ) < 30
            THEN '<30 days'

        WHEN DATE_DIFF(
                'day',
                CAST(a.created_at AS DATE),
                CURRENT_DATE
             ) < 90
            THEN '30-89 days'

        WHEN DATE_DIFF(
                'day',
                CAST(a.created_at AS DATE),
                CURRENT_DATE
             ) < 180
            THEN '90-179 days'

        ELSE '180+ days'
    END AS account_age_bucket,

    -- Trial metrics
    CASE
        WHEN a.trial_start_date IS NOT NULL
         AND a.trial_end_date IS NOT NULL
        THEN DATE_DIFF(
            'day',
            a.trial_start_date,
            a.trial_end_date
        )
        ELSE NULL
    END AS trial_length_days,

    -- Status and flags
    a.account_status,
    (a.account_status = 'active')          AS is_active_account,
    (a.trial_start_date IS NOT NULL)       AS has_trial

FROM bronze_accounts a
LEFT JOIN silver_geography g
    ON UPPER(a.country_code) = g.country_code
""")

print("✅ Created silver_accounts")

con.close()