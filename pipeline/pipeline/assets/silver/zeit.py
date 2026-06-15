"""Silver layer: populate core.dim_zeit (date dimension)."""

import pandas as pd
from dagster import AssetExecutionContext, Output, asset

from pipeline.resources import DatabaseResource


@asset(
    group_name="silver",
    description="Populate core.dim_zeit with year/quarter combinations.",
    required_resource_keys={"database"},
)
def dim_zeit(context: AssetExecutionContext, database: DatabaseResource) -> Output:
    years = range(2018, 2026)
    rows = [
        {"berichtsjahr": y, "quartal": q}
        for y in years
        for q in range(1, 5)
    ]
    df = pd.DataFrame(rows)

    with database.get_sync_session() as session:
        df.to_sql(
            "dim_zeit",
            con=session.connection(),
            schema="core",
            if_exists="append",
            index=False,
            method="multi",
        )
        # Remove duplicates (idempotent re-runs)
        session.execute(__import__("sqlalchemy").text("""
            DELETE FROM core.dim_zeit a
            USING core.dim_zeit b
            WHERE a.ctid < b.ctid
              AND a.berichtsjahr = b.berichtsjahr
              AND a.quartal = b.quartal
        """))

    context.log.info(f"Populated dim_zeit with {len(rows)} rows")
    return Output(value=len(rows), metadata={"row_count": len(rows)})
