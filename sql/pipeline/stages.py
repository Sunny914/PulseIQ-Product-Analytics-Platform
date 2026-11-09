"""Ordered pipeline stages derived from actual script table dependencies."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from db_config import get_repo_root

REPO_ROOT = get_repo_root()
SQL = REPO_ROOT / "sql"


class StageGroup(str, Enum):
    VALIDATE = "validate"
    RAW = "raw"
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    EXPORT = "export"
    DQ = "dq"
    EXPORT_VALIDATE = "export_validate"


@dataclass(frozen=True)
class PipelineStage:
    stage_id: str
    group: StageGroup
    description: str
    script: Path | None = None
    internal: bool = False


# Geography bronze/silver handled by orchestrator (mode-dependent); IDs reserved in graph.
STAGE_VALIDATE_SNAPSHOT = PipelineStage(
    "validate_snapshot",
    StageGroup.VALIDATE,
    "Validate Parquet snapshots and MANIFEST.json",
    SQL / "validate_raw_snapshot.py",
)
STAGE_LOAD_RAW = PipelineStage(
    "load_raw",
    StageGroup.RAW,
    "Load raw__* tables from snapshots",
    SQL / "load_raw.py",
)

BRONZE_STAGES = [
    PipelineStage("bronze_accounts", StageGroup.BRONZE, "Bronze accounts", SQL / "bronze" / "bronze_accounts.py"),
    PipelineStage("bronze_users", StageGroup.BRONZE, "Bronze users", SQL / "bronze" / "bronze_users.py"),
    PipelineStage("bronze_deals", StageGroup.BRONZE, "Bronze deals", SQL / "bronze" / "bronze_deals.py"),
    PipelineStage(
        "bronze_product_events",
        StageGroup.BRONZE,
        "Bronze product events",
        SQL / "bronze" / "bronze_product_events.py",
    ),
]

STAGE_GEOGRAPHY = PipelineStage(
    "geography",
    StageGroup.BRONZE,
    "Geography bronze/silver (mode-dependent)",
    internal=True,
)

SILVER_STAGES = [
    PipelineStage(
        "silver_geography",
        StageGroup.SILVER,
        "Silver geography (source mode only)",
        SQL / "silver" / "silver_geography.py",
    ),
    PipelineStage("silver_accounts", StageGroup.SILVER, "Silver accounts", SQL / "silver" / "silver_accounts.py"),
    PipelineStage("silver_users", StageGroup.SILVER, "Silver users", SQL / "silver" / "silver_users.py"),
    PipelineStage("silver_deals", StageGroup.SILVER, "Silver deals", SQL / "silver" / "silver_deals.py"),
    PipelineStage(
        "silver_product_events",
        StageGroup.SILVER,
        "Silver product events (attribution)",
        SQL / "silver" / "silver_product_events.py",
    ),
]

GOLD_STAGES = [
    PipelineStage("gold_dim_accounts", StageGroup.GOLD, "Gold dim accounts", SQL / "gold" / "gold_dim_accounts.py"),
    PipelineStage("gold_dim_users", StageGroup.GOLD, "Gold dim users", SQL / "gold" / "gold_dim_users.py"),
    PipelineStage("gold_fact_deals", StageGroup.GOLD, "Gold fact deals", SQL / "gold" / "gold_fact_deals.py"),
    PipelineStage(
        "gold_fact_product_events",
        StageGroup.GOLD,
        "Gold fact product events",
        SQL / "gold" / "gold_fact_product_events.py",
    ),
    PipelineStage(
        "gold_fact_qualified_product_events",
        StageGroup.GOLD,
        "Qualified events with chronology flags",
        SQL / "gold" / "gold_fact_qualified_product_events.py",
    ),
    PipelineStage(
        "gold_fact_engagement_periodic",
        StageGroup.GOLD,
        "Gold engagement DAU/WAU/MAU",
        SQL / "gold" / "gold_fact_engagement_periodic.py",
    ),
    PipelineStage(
        "gold_fact_feature_adoption_account",
        StageGroup.GOLD,
        "Gold account feature adoption",
        SQL / "gold" / "gold_fact_feature_adoption_account.py",
    ),
    PipelineStage(
        "gold_fact_feature_adoption_user",
        StageGroup.GOLD,
        "Gold user feature adoption",
        SQL / "gold" / "gold_fact_feature_adoption_user.py",
    ),
    PipelineStage(
        "gold_fact_feature_adoption_by_period",
        StageGroup.GOLD,
        "Gold feature adoption by period",
        SQL / "gold" / "gold_fact_feature_adoption_by_period.py",
    ),
    PipelineStage(
        "gold_fact_feature_breadth",
        StageGroup.GOLD,
        "Gold feature breadth (account/user)",
        SQL / "gold" / "gold_fact_feature_breadth.py",
    ),
    PipelineStage(
        "gold_fact_product_activity_recency",
        StageGroup.GOLD,
        "Gold product activity recency",
        SQL / "gold" / "gold_fact_product_activity_recency.py",
    ),
    PipelineStage(
        "gold_fact_retention_cohort",
        StageGroup.GOLD,
        "Retention D7/D14 cohorts",
        SQL / "gold" / "gold_fact_retention_cohort.py",
    ),
    PipelineStage(
        "gold_fact_account_workflow_funnel",
        StageGroup.GOLD,
        "Descriptive account workflow funnel",
        SQL / "gold" / "gold_fact_account_workflow_funnel.py",
    ),
    PipelineStage(
        "gold_fact_product_events_aggregated",
        StageGroup.GOLD,
        "Gold aggregated product events",
        SQL / "gold" / "gold_fact_product_events_aggregated.py",
    ),
    PipelineStage(
        "gold_fact_advanced_activation",
        StageGroup.GOLD,
        "Gold advanced activation",
        SQL / "gold" / "gold_fact_advanced_activation.py",
    ),
    PipelineStage(
        "gold_fact_activation_as_of",
        StageGroup.GOLD,
        "Gold activation as-of",
        SQL / "gold" / "gold_fact_activation_as_of.py",
    ),
    PipelineStage(
        "gold_fact_segment_product_metrics",
        StageGroup.GOLD,
        "Segment engagement summary",
        SQL / "gold" / "gold_fact_segment_product_metrics.py",
    ),
    PipelineStage(
        "gold_dim_geography",
        StageGroup.GOLD,
        "Gold dim geography",
        SQL / "gold" / "gold_dim_geography.py",
    ),
]

STAGE_EXPORT = PipelineStage(
    "export_gold_csv",
    StageGroup.EXPORT,
    "Export Gold tables to CSV",
    SQL / "gold" / "export_gold_to_csv.py",
)

STAGE_DQ = PipelineStage(
    "data_quality",
    StageGroup.DQ,
    "Warehouse data-quality contracts",
    internal=True,
)

STAGE_EXPORT_VALIDATE = PipelineStage(
    "export_validate",
    StageGroup.EXPORT_VALIDATE,
    "Validate Gold CSV exports",
    internal=True,
)


def planned_stage_ids(*, geography_mode: str, include_dq: bool = True) -> list[str]:
    """Execution order for dry-run and reporting."""
    ids = [
        STAGE_VALIDATE_SNAPSHOT.stage_id,
        STAGE_LOAD_RAW.stage_id,
    ]
    ids.extend(s.stage_id for s in BRONZE_STAGES)
    ids.append(STAGE_GEOGRAPHY.stage_id)
    if geography_mode == "source":
        ids.append("silver_geography")
    ids.extend(
        s.stage_id
        for s in SILVER_STAGES
        if s.stage_id != "silver_geography" or geography_mode == "source"
    )
    ids.extend(s.stage_id for s in GOLD_STAGES)
    ids.append(STAGE_EXPORT.stage_id)
    if include_dq:
        ids.append(STAGE_DQ.stage_id)
        ids.append(STAGE_EXPORT_VALIDATE.stage_id)
    return ids
