import duckdb
import os

con = duckdb.connect(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "product_analytics_light.db"
    )
)

con.execute("""
CREATE OR REPLACE TABLE gold_fact_deals AS
SELECT

    deal_id                 AS DealId,
    account_id              AS AccountId,
    owner_user_id           AS OwnerUserId,

    pipeline_id             AS PipelineId,
    current_stage_id        AS StageId,

    status                  AS Status,

    created_at              AS CreatedAt,
    created_date            AS CreatedDate,

    closed_at               AS ClosedAt,
    closed_date             AS ClosedDate,

    last_stage_changed_at   AS LastStageChangedAt,
    last_stage_changed_date AS LastStageChangedDate,

    amount                  AS DealAmount,
    currency                AS Currency,
    country_code            AS CountryCode,

    source_system           AS SourceSystem,

    is_closed               AS IsClosed,
    is_won                  AS IsWon,

    deal_cycle_days         AS DealCycleDays,
    deal_age_days           AS DealAgeDays

FROM silver_deals
ORDER BY DealId
""")

print("✅ Created gold_fact_deals")

con.close()