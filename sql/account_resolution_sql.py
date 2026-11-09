"""
WS-5.2 account attribution SQL fragments for silver_product_events.

Requires bronze_accounts, silver_users, and raw__deals to exist in the same database.
"""

VALID_ACCOUNTS_CTE = """
valid_accounts AS (
    SELECT DISTINCT account_id
    FROM bronze_accounts
    WHERE account_id IS NOT NULL
),
"""

DEAL_ACCOUNT_UNAMBIGUOUS_CTE = """
deal_account_unambiguous AS (
    SELECT
        d.deal_id,
        MIN(d.account_id) AS deal_account_id
    FROM raw__deals AS d
    INNER JOIN valid_accounts AS va
        ON d.account_id = va.account_id
    WHERE d.deal_id IS NOT NULL
    GROUP BY d.deal_id
    HAVING COUNT(DISTINCT d.account_id) = 1
),
"""

USER_ACCOUNT_MAP_CTE = """
user_account_map AS (
    SELECT
        u.user_id,
        u.account_id AS user_account_id
    FROM silver_users AS u
    INNER JOIN valid_accounts AS va
        ON u.account_id = va.account_id
    WHERE u.user_id IS NOT NULL
),
"""

ACCOUNT_RESOLUTION_COLUMNS = """
    CASE
        WHEN w.account_id IS NOT NULL
             AND va.account_id IS NOT NULL
            THEN w.account_id
        WHEN w.account_id IS NULL
             AND um.user_account_id IS NOT NULL
             AND da.deal_account_id IS NOT NULL
             AND um.user_account_id = da.deal_account_id
            THEN um.user_account_id
        WHEN w.account_id IS NULL
             AND um.user_account_id IS NOT NULL
             AND da.deal_account_id IS NULL
            THEN um.user_account_id
        WHEN w.account_id IS NULL
             AND um.user_account_id IS NULL
             AND da.deal_account_id IS NOT NULL
            THEN da.deal_account_id
        ELSE NULL
    END AS account_id_resolved,

    CASE
        WHEN w.account_id IS NOT NULL
             AND va.account_id IS NOT NULL
            THEN 'SOURCE_VERIFIED'
        WHEN w.account_id IS NOT NULL
             AND va.account_id IS NULL
            THEN 'QUARANTINED'
        WHEN w.account_id IS NULL
             AND um.user_account_id IS NOT NULL
             AND da.deal_account_id IS NOT NULL
             AND um.user_account_id = da.deal_account_id
            THEN 'ENRICHED'
        WHEN w.account_id IS NULL
             AND um.user_account_id IS NOT NULL
             AND da.deal_account_id IS NOT NULL
             AND um.user_account_id <> da.deal_account_id
            THEN 'QUARANTINED'
        WHEN w.account_id IS NULL
             AND um.user_account_id IS NOT NULL
             AND da.deal_account_id IS NULL
            THEN 'ENRICHED'
        WHEN w.account_id IS NULL
             AND um.user_account_id IS NULL
             AND da.deal_account_id IS NOT NULL
            THEN 'ENRICHED'
        ELSE 'QUARANTINED'
    END AS account_resolution_status,

    CASE
        WHEN w.account_id IS NOT NULL
             AND va.account_id IS NOT NULL
            THEN 'SOURCE'
        WHEN w.account_id IS NOT NULL
             AND va.account_id IS NULL
            THEN 'NONE'
        WHEN w.account_id IS NULL
             AND um.user_account_id IS NOT NULL
             AND da.deal_account_id IS NOT NULL
             AND um.user_account_id = da.deal_account_id
            THEN 'USER_DEAL_CONSISTENT'
        WHEN w.account_id IS NULL
             AND um.user_account_id IS NOT NULL
             AND da.deal_account_id IS NOT NULL
             AND um.user_account_id <> da.deal_account_id
            THEN 'NONE'
        WHEN w.account_id IS NULL
             AND um.user_account_id IS NOT NULL
             AND da.deal_account_id IS NULL
            THEN 'USER_DIM'
        WHEN w.account_id IS NULL
             AND um.user_account_id IS NULL
             AND da.deal_account_id IS NOT NULL
            THEN 'DEAL_RAW'
        ELSE 'NONE'
    END AS account_resolution_method,

    CASE
        WHEN w.account_id IS NOT NULL
             AND va.account_id IS NOT NULL
            THEN 'SOURCE_ACCOUNT_VERIFIED'
        WHEN w.account_id IS NOT NULL
             AND va.account_id IS NULL
            THEN 'INVALID_SOURCE_ACCOUNT_REFERENCE'
        WHEN w.account_id IS NULL
             AND um.user_account_id IS NOT NULL
             AND da.deal_account_id IS NOT NULL
             AND um.user_account_id = da.deal_account_id
            THEN 'USER_DEAL_ACCOUNT_AGREE'
        WHEN w.account_id IS NULL
             AND um.user_account_id IS NOT NULL
             AND da.deal_account_id IS NOT NULL
             AND um.user_account_id <> da.deal_account_id
            THEN 'CONFLICTING_USER_DEAL_ACCOUNTS'
        WHEN w.account_id IS NULL
             AND um.user_account_id IS NOT NULL
             AND da.deal_account_id IS NULL
            THEN 'USER_ACCOUNT_ONLY'
        WHEN w.account_id IS NULL
             AND um.user_account_id IS NULL
             AND da.deal_account_id IS NOT NULL
            THEN 'DEAL_ACCOUNT_ONLY'
        ELSE 'NO_VALID_ACCOUNT_REFERENCE'
    END AS account_resolution_reason
"""
