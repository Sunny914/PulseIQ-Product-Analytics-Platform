import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db_config import connect_duckdb

con = connect_duckdb()

con.execute("""
CREATE OR REPLACE TABLE gold_dim_users AS
SELECT

    user_id             AS UserId,
    account_id          AS AccountId,

    full_name           AS FullName,
    email_domain        AS EmailDomain,
    job_role            AS JobRole,
    user_status         AS UserStatus,

    is_active_user      AS IsActiveUser,
    is_admin            AS IsAdmin,

    created_at          AS CreatedAt,
    created_date        AS CreatedDate,
    last_seen_at        AS LastSeenAt,

    is_future_created   AS IsFutureCreated,
    user_tenure_days    AS UserTenureDays,
    account_tenure_days AS AccountTenureDays,
    days_since_last_seen AS DaysSinceLastSeen,
    recency_bucket      AS RecencyBucket

FROM silver_users
ORDER BY UserId
""")

print("✅ Created gold_dim_users")

con.close()