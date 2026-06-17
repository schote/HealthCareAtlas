"""Silver layer: populate core.dim_zeit (date dimension)."""

from sqlalchemy import text
from dagster import AssetExecutionContext, Output, asset

from pipeline.resources import DatabaseResource

_YEAR_START = 2018
_YEAR_END = 2025


@asset(
    group_name="silver",
    description="Populate core.dim_zeit with year/quarter combinations.",
)
def dim_zeit(context: AssetExecutionContext, database: DatabaseResource) -> Output:
    with database.get_sync_session() as session:
        result = session.execute(text("""
            INSERT INTO core.dim_zeit (berichtsjahr, quartal)
            SELECT y, q
            FROM generate_series(:year_start, :year_end) AS y,
                 generate_series(1, 4) AS q
            ON CONFLICT DO NOTHING
        """), {"year_start": _YEAR_START, "year_end": _YEAR_END})
        inserted = result.rowcount

    row_count = (_YEAR_END - _YEAR_START + 1) * 4
    context.log.info(f"dim_zeit: {inserted} new rows inserted ({row_count} total slots)")
    return Output(value=inserted, metadata={"inserted": inserted, "total_slots": row_count})
