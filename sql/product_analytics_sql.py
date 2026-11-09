"""
WS-12/WS-13 shared filters, attribution, and chronology rules for product analytics.

Chronology (WS-13): official metrics exclude events before entity creation.
AS_OF metrics also require entity CreatedDate <= ReportAsOfDate.
Source data may contain PRE_CREATION_EVENT rows; they are not rewritten.
"""

from __future__ import annotations

USER_OFFICIAL_PREDICATE = """
    e.AccountResolutionStatus = 'SOURCE_VERIFIED'
    AND e.UserId IS NOT NULL
"""

USER_SENSITIVITY_PREDICATE = """
    e.AccountResolutionStatus IN ('SOURCE_VERIFIED', 'ENRICHED')
    AND e.UserId IS NOT NULL
"""

ACCOUNT_OFFICIAL_PREDICATE = """
    e.AccountResolutionStatus = 'SOURCE_VERIFIED'
    AND e.AccountId IS NOT NULL
"""

ACCOUNT_SENSITIVITY_PREDICATE = """
    e.AccountResolutionStatus IN ('SOURCE_VERIFIED', 'ENRICHED')
    AND e.AccountIdResolved IS NOT NULL
"""

VALID_PRODUCT_FEATURES: tuple[str, ...] = (
    "dashboard",
    "automation",
    "pipeline",
    "deal",
)

FEATURE_IN_LIST_SQL = ", ".join(f"'{f}'" for f in VALID_PRODUCT_FEATURES)

FUNNEL_STAGES: tuple[str, ...] = (
    "login",
    "view_dashboard",
    "create_deal",
    "move_deal_stage",
    "log_activity",
)


def feature_is_valid_sql(column: str = "e.FeatureName") -> str:
    return f"{column} IN ({FEATURE_IN_LIST_SQL})"


def as_of_event_predicate(as_of_literal: str, alias: str = "e") -> str:
    return f"{alias}.EventDate <= {as_of_literal}"


def account_chronology_predicate(account_created_col: str = "AccountCreatedDate", event_date_col: str = "EventDate") -> str:
    return f"{event_date_col} >= {account_created_col}"


def user_chronology_predicate(user_created_col: str = "UserCreatedDate", event_date_col: str = "EventDate") -> str:
    return f"{event_date_col} >= {user_created_col}"


def account_entity_mature_as_of(as_of_literal: str, account_created_col: str = "AccountCreatedDate") -> str:
    return f"{account_created_col} <= {as_of_literal}"


def user_entity_mature_as_of(as_of_literal: str, user_created_col: str = "UserCreatedDate") -> str:
    return f"{user_created_col} <= {as_of_literal}"
