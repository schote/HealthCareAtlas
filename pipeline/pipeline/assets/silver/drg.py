"""Silver layer: aggregate raw §21 DRG case data into core.fact_drg."""

import pandas as pd
from dagster import AssetExecutionContext, Output, StaticPartitionsDefinition, asset
from sqlalchemy import text

from pipeline.resources import DatabaseResource

BERICHTSJAHRE = StaticPartitionsDefinition(["2020", "2021", "2022", "2023"])


@asset(
    group_name="silver",
    partitions_def=BERICHTSJAHRE,
    deps=["drg_raw"],
    description="Cast and load raw.drg_fallzahlen → core.fact_drg for one Berichtsjahr.",
)
def fact_drg(context: AssetExecutionContext, database: DatabaseResource) -> Output:
    """
    Read raw §21 DRG rows from Bronze, cast TEXT columns to numeric types,
    and bulk-load into core.fact_drg. Replaces any existing rows for the partition year.
    """
    berichtsjahr = int(context.partition_key)

    with database.get_sync_session() as session:
        df = pd.read_sql(
            "SELECT ik_nummer, drg_code, fallzahl, verweildauer, casemix_index "
            "FROM raw.drg_fallzahlen WHERE berichtsjahr = %(year)s",
            con=session.connection(),
            params={"year": berichtsjahr},
        )

    context.log.info(f"Read {len(df)} raw DRG rows for {berichtsjahr}")

    df = df.dropna(subset=["ik_nummer", "drg_code"])
    df["ik_nummer"] = df["ik_nummer"].str.strip().str.zfill(9)
    df["fallzahl"] = pd.to_numeric(df["fallzahl"], errors="coerce").astype("Int64")
    df["verweildauer"] = pd.to_numeric(df["verweildauer"], errors="coerce")
    df["casemix_index"] = pd.to_numeric(df["casemix_index"], errors="coerce")
    df["berichtsjahr"] = berichtsjahr

    if df.empty:
        context.log.warning(f"No usable DRG rows for {berichtsjahr}")
        return Output(value=0, metadata={"inserted_rows": 0, "berichtsjahr": berichtsjahr})

    with database.get_sync_session() as session:
        session.execute(
            text("DELETE FROM core.fact_drg WHERE berichtsjahr = :year"),
            {"year": berichtsjahr},
        )
        df[["ik_nummer", "berichtsjahr", "drg_code", "fallzahl", "verweildauer", "casemix_index"]].to_sql(
            "fact_drg",
            con=session.connection(),
            schema="core",
            if_exists="append",
            index=False,
            method="multi",
            chunksize=2000,
        )
        session.commit()

    context.log.info(f"Loaded {len(df)} fact_drg rows for {berichtsjahr}")
    return Output(value=len(df), metadata={"inserted_rows": len(df), "berichtsjahr": berichtsjahr})
