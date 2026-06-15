"""Bronze layer: ingest raw §21 DRG case data CSV files from InEK/FDZ."""

from pathlib import Path

import pandas as pd
from dagster import AssetExecutionContext, Output, StaticPartitionsDefinition, asset

from pipeline.resources import DatabaseResource

BERICHTSJAHRE = StaticPartitionsDefinition(["2020", "2021", "2022", "2023"])

DRG_COLUMNS = {
    "IK": "ik_nummer",
    "Standort": "standort_id",
    "DRG": "drg_code",
    "Fallzahl": "fallzahl",
    "Verweildauer_mean": "verweildauer",
    "CMI": "casemix_index",
}


@asset(
    group_name="bronze",
    partitions_def=BERICHTSJAHRE,
    description="Raw §21 DRG case data CSV → raw.drg_fallzahlen rows (append-only).",
    required_resource_keys={"database"},
)
def drg_raw(context: AssetExecutionContext, database: DatabaseResource) -> Output:
    """
    Ingest annual §21 DRG case data from InEK/FDZ into the Bronze layer.

    Files are placed under data/raw/drg/<berichtsjahr>/*.csv.
    Each row represents one DRG code per hospital per year.
    """
    berichtsjahr = int(context.partition_key)
    data_dir = Path("/data/raw/drg") / str(berichtsjahr)

    csv_files = sorted(data_dir.glob("*.csv")) if data_dir.exists() else []
    context.log.info(f"Found {len(csv_files)} DRG CSV files for {berichtsjahr}")

    dfs: list[pd.DataFrame] = []
    for csv_file in csv_files:
        df = pd.read_csv(csv_file, sep=";", dtype=str, encoding="utf-8")
        df = df.rename(columns={k: v for k, v in DRG_COLUMNS.items() if k in df.columns})
        df["berichtsjahr"] = berichtsjahr
        df["source_file"] = csv_file.name
        df["ingested_at"] = pd.Timestamp.utcnow()
        dfs.append(df)

    row_count = 0
    if dfs:
        combined = pd.concat(dfs, ignore_index=True)
        row_count = len(combined)
        with database.get_sync_session() as session:
            combined.to_sql(
                "drg_fallzahlen",
                con=session.connection(),
                schema="raw",
                if_exists="append",
                index=False,
                method="multi",
                chunksize=5000,
            )

    context.log.info(f"Ingested {row_count} raw DRG rows for {berichtsjahr}")
    return Output(value=row_count, metadata={"row_count": row_count, "berichtsjahr": berichtsjahr})
