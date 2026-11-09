"""Required WS-9 warehouse contracts for pipeline gate (no pytest)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import duckdb


@dataclass
class DQResult:
    passed: bool
    checks: dict[str, object] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


def run_pipeline_dq(db_path: Path) -> DQResult:
    errors: list[str] = []
    checks: dict[str, object] = {}
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        raw_events = con.execute("SELECT COUNT(*) FROM raw__product_events").fetchone()[0]
        bronze_events = con.execute("SELECT COUNT(*) FROM bronze_product_events").fetchone()[0]
        silver_events = con.execute("SELECT COUNT(*) FROM silver_product_events").fetchone()[0]
        test_removed = con.execute(
            "SELECT COUNT(*) FROM bronze_product_events WHERE is_test_event"
        ).fetchone()[0]
        gold_detail = con.execute("SELECT COUNT(*) FROM gold_fact_product_events").fetchone()[0]
        agg_sum = con.execute(
            "SELECT COALESCE(SUM(EventCount), 0) FROM gold_fact_product_events_aggregated"
        ).fetchone()[0]

        checks.update(
            {
                "raw_product_events": raw_events,
                "bronze_product_events": bronze_events,
                "silver_product_events": silver_events,
                "test_events_removed": test_removed,
                "gold_fact_product_events": gold_detail,
                "aggregated_event_count_sum": agg_sum,
            }
        )

        if raw_events != 61747:
            errors.append(f"raw__product_events expected 61747 got {raw_events}")
        if bronze_events != raw_events:
            errors.append("bronze_product_events != raw__product_events")
        if bronze_events - test_removed != silver_events != 60552:
            errors.append(
                f"silver grain expected 60552 (bronze {bronze_events} - test {test_removed})"
            )
        if gold_detail != 60552 or agg_sum != gold_detail:
            errors.append("gold detail/aggregated reconciliation failed")

        statuses = dict(
            con.execute(
                """
                SELECT account_resolution_status, COUNT(*)
                FROM silver_product_events
                GROUP BY 1
                """
            ).fetchall()
        )
        checks["attribution"] = statuses
        if statuses.get("SOURCE_VERIFIED") != 59911:
            errors.append("SOURCE_VERIFIED expected 59911")
        if statuses.get("ENRICHED") != 226:
            errors.append("ENRICHED expected 226")
        if statuses.get("QUARANTINED") != 415:
            errors.append("QUARANTINED expected 415")

        act = con.execute(
            """
            SELECT COUNT(*),
                   SUM(CASE WHEN IsActivated THEN 1 ELSE 0 END),
                   AVG(TimeToValueDays) FILTER (WHERE IsActivated)
            FROM gold_fact_advanced_activation
            """
        ).fetchone()
        checks["activation_accounts"] = act[0]
        checks["activation_activated"] = act[1]
        checks["activation_mean_ttv"] = float(act[2]) if act[2] is not None else None

        if act[0] != 120 or act[1] != 21:
            errors.append("activation full-dataset expected 21/120")
        if act[2] is not None and abs(float(act[2]) - 9.904761904761905) > 1e-5:
            errors.append(f"mean TTV expected ~9.904762 got {act[2]}")

        asof = con.execute(
            """
            SELECT
                SUM(CASE WHEN IsEligibleAsOf THEN 1 ELSE 0 END),
                SUM(CASE WHEN IsEligibleAsOf AND IsActivatedAsOf THEN 1 ELSE 0 END)
            FROM gold_fact_activation_as_of
            """
        ).fetchone()
        checks["asof_eligible"] = asof[0]
        checks["asof_activated"] = asof[1]
        if asof != (15, 0):
            errors.append(f"as-of activation expected (15, 0) got {asof}")

        event_sk_nulls = con.execute(
            "SELECT COUNT(*) FROM silver_product_events WHERE event_sk IS NULL"
        ).fetchone()[0]
        if event_sk_nulls != 0:
            errors.append("event_sk must be non-null")
    finally:
        con.close()

    return DQResult(passed=not errors, checks=checks, errors=errors)
