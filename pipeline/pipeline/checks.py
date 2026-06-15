"""Asset checks for freshness and data quality validation."""

from dagster import AssetCheckResult, AssetCheckSeverity, asset_check
from sqlalchemy import text

from pipeline.resources import DatabaseResource


@asset_check(asset="einrichtung_kpi", description="Ensure KPI data is not older than 14 months.")
def kpi_freshness_check(database: DatabaseResource) -> AssetCheckResult:
    with database.get_sync_session() as session:
        result = session.execute(text("""
            SELECT MAX(datenstand) AS latest_date,
                   NOW() - MAX(datenstand)::timestamp AS age
            FROM mart.einrichtung_kpi
        """)).fetchone()

    if result is None or result.latest_date is None:
        return AssetCheckResult(
            passed=False,
            severity=AssetCheckSeverity.WARN,
            description="mart.einrichtung_kpi is empty — no data ingested yet.",
        )

    age_days = result.age.days if result.age else 0
    passed = age_days <= 425  # ~14 months
    return AssetCheckResult(
        passed=passed,
        severity=AssetCheckSeverity.WARN,
        description=f"Latest KPI data is {age_days} days old (latest: {result.latest_date}).",
        metadata={"latest_date": str(result.latest_date), "age_days": age_days},
    )


@asset_check(
    asset="einrichtung_kpi",
    description="Ensure deficit index values are within the valid 0–100 range.",
)
def kpi_range_check(database: DatabaseResource) -> AssetCheckResult:
    with database.get_sync_session() as session:
        result = session.execute(text("""
            SELECT COUNT(*) AS invalid_count
            FROM mart.einrichtung_kpi
            WHERE def_index < 0 OR def_index > 100
        """)).fetchone()

    invalid = result.invalid_count if result else 0
    return AssetCheckResult(
        passed=invalid == 0,
        severity=AssetCheckSeverity.ERROR,
        description=f"{invalid} KPI rows have def_index outside [0, 100].",
        metadata={"invalid_rows": invalid},
    )


@asset_check(
    asset="einrichtung_kpi",
    description="Ensure confidence score is present and valid (0–1) for all KPIs.",
)
def kpi_confidence_check(database: DatabaseResource) -> AssetCheckResult:
    with database.get_sync_session() as session:
        result = session.execute(text("""
            SELECT
                COUNT(*) FILTER (WHERE konfidenz IS NULL)         AS null_count,
                COUNT(*) FILTER (WHERE konfidenz < 0 OR konfidenz > 1) AS out_of_range
            FROM mart.einrichtung_kpi
        """)).fetchone()

    issues = (result.null_count or 0) + (result.out_of_range or 0)
    return AssetCheckResult(
        passed=issues == 0,
        severity=AssetCheckSeverity.WARN,
        description=f"{issues} KPI rows with invalid or missing konfidenz score.",
        metadata={
            "null_konfidenz": result.null_count or 0,
            "out_of_range_konfidenz": result.out_of_range or 0,
        },
    )
