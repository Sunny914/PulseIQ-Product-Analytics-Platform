"""
Expected Gold table column names for validation and export documentation.
"""

from __future__ import annotations

GOLD_FACT_PRODUCT_EVENTS_AGGREGATED_COLUMNS: tuple[str, ...] = (
    "EventDate",
    "EventNameNormalized",
    "EventCategory",
    "FeatureName",
    "AccountId",
    "EventCount",
    "UniqueUsers",
    "SourceEventNames",
)

GOLD_FACT_ACTIVATION_AS_OF_COLUMNS: tuple[str, ...] = (
    "AccountId",
    "CreatedDate",
    "ReportAsOfDate",
    "ActivationWindowEndDate",
    "IsFutureCreated",
    "IsWindowCompleteAsOf",
    "IsEligibleAsOf",
    "IsActivatedFullDataset",
    "IsActivatedAsOf",
    "TimeToValueDaysFullDataset",
    "TimeToValueDaysAsOf",
)

GOLD_FACT_PRODUCT_EVENTS_DETAIL_COLUMNS: tuple[str, ...] = (
    "EventSk",
    "EventId",
    "AccountId",
    "AccountIdResolved",
    "AccountResolutionStatus",
    "AccountResolutionMethod",
    "AccountResolutionReason",
    "UserId",
    "DealId",
    "EventName",
    "EventNameNormalized",
    "EventCategory",
    "HasDealContext",
    "EventTimestamp",
    "EventDate",
    "EventMonth",
    "EventProperties",
    "EventPropertiesParseStatus",
    "FeatureName",
    "EventSource",
    "PipelineId",
    "StageId",
    "Platform",
    "DeviceType",
    "AppVersion",
    "CountryCode",
    "SourceSystem",
)

# DuckDB table name -> CSV filename under exports/gold_csv/
GOLD_TABLE_CSV_FILENAMES: dict[str, str] = {
    "gold_dim_accounts": "dim_accounts.csv",
    "gold_dim_geography": "dim_geography.csv",
    "gold_dim_users": "dim_users.csv",
    "gold_fact_advanced_activation": "fact_advanced_activation.csv",
    "gold_fact_activation_as_of": "fact_activation_as_of.csv",
    "gold_fact_deals": "fact_deals.csv",
    "gold_fact_product_events": "fact_product_events.csv",
    "gold_fact_product_events_aggregated": "fact_product_events_aggregated.csv",
    "gold_fact_engagement_periodic": "fact_engagement_periodic.csv",
    "gold_fact_feature_adoption_account": "fact_feature_adoption_account.csv",
    "gold_fact_feature_adoption_user": "fact_feature_adoption_user.csv",
    "gold_fact_feature_adoption_by_period": "fact_feature_adoption_by_period.csv",
    "gold_fact_feature_breadth_account": "fact_feature_breadth_account.csv",
    "gold_fact_feature_breadth_user": "fact_feature_breadth_user.csv",
    "gold_fact_product_activity_recency_account": "fact_product_activity_recency_account.csv",
    "gold_fact_product_activity_recency_user": "fact_product_activity_recency_user.csv",
    "gold_fact_qualified_product_events": "fact_qualified_product_events.csv",
    "gold_fact_retention_cohort": "fact_retention_cohort.csv",
    "gold_fact_account_workflow_funnel": "fact_account_workflow_funnel.csv",
    "gold_fact_segment_product_metrics": "fact_segment_product_metrics.csv",
}
