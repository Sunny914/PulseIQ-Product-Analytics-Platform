"""Geography bronze/silver preparation (source Excel vs derived fixture)."""

from __future__ import annotations

from enum import Enum
from pathlib import Path

import duckdb

from db_config import get_repo_root

GEO_XLSX = get_repo_root() / "sql" / "data" / "raw_geography.xlsx"


class GeographyMode(str, Enum):
    SOURCE = "source"
    DERIVED_FIXTURE = "derived-fixture"


def geography_excel_available() -> bool:
    return GEO_XLSX.is_file()


def apply_derived_geography_fixture(db_path: Path) -> None:
    """
    Deterministic geography stub from distinct account country codes.

    Does not recreate the original missing Excel source.
    """
    con = duckdb.connect(str(db_path))
    try:
        con.execute(
            """
            CREATE OR REPLACE TABLE bronze_geography AS
            SELECT DISTINCT
                UPPER(TRIM(country_code)) AS country_code,
                UPPER(TRIM(country_code)) AS country_name,
                CAST(NULL AS VARCHAR) AS region,
                CAST(NULL AS VARCHAR) AS market,
                CAST(NULL AS VARCHAR) AS currency,
                CAST(NULL AS VARCHAR) AS sales_region
            FROM raw__accounts
            WHERE country_code IS NOT NULL
            """
        )
        con.execute(
            """
            CREATE OR REPLACE TABLE silver_geography AS
            SELECT * FROM bronze_geography
            """
        )
    finally:
        con.close()
