"""Bronze layer: ingest raw PpUGV (nursing staff minimum) CSV data from InEK Pflege."""

from pathlib import Path

import pandas as pd
from dagster import AssetExecutionContext, Output, StaticPartitionsDefinition, asset

from pipeline.resources import DatabaseResource

# Quarterly partitions: YYYY-QN
QUARTALE = StaticPartitionsDefinition([
    f"{year}-Q{q}" for year in range(2020, 2025) for q in range(1, 5)
])


@asset(
    group_name="bronze",
    partitions_def=QUARTALE,
    description="Raw PpUGV nursing staff data CSV → raw.ppugv rows (append-only).",
    required_resource_keys={"database"},
)
def ppugv_raw(context: AssetExecutionContext, database: DatabaseResource) -> Output:
    """
    Ingest quarterly PpUGV (Pflegepersonaluntergrenzen-Verordnung) data
    from InEK Pflege into the Bronze layer.

    Files are placed under data/raw/ppugv/<year>/<quarter>/*.csv.
    Each row represents nursing compliance per ward area per hospital per quarter.
    """
    year_str, quarter_str = context.partition_key.split("-")
    year = int(year_str)
    quarter = int(quarter_str[1])

    data_dir = Path("/data/raw/ppugv") / year_str / quarter_str
    csv_files = sorted(data_dir.glob("*.csv")) if data_dir.exists() else []
    context.log.info(f"Found {len(csv_files)} PpUGV CSV files for {year}-Q{quarter}")

    dfs: list[pd.DataFrame] = []
    for csv_file in csv_files:
        df = pd.read_csv(csv_file, sep=";", dtype=str, encoding="utf-8")
        df["berichtsjahr"] = year
        df["quartal"] = quarter
        df["source_file"] = csv_file.name
        df["ingested_at"] = pd.Timestamp.utcnow()
        dfs.append(df)

    row_count = 0
    if dfs:
        combined = pd.concat(dfs, ignore_index=True)
        row_count = len(combined)
        with database.get_sync_session() as session:
            combined.to_sql(
                "ppugv",
                con=session.connection(),
                schema="raw",
                if_exists="append",
                index=False,
                method="multi",
                chunksize=5000,
            )

    return Output(value=row_count, metadata={"row_count": row_count, "partition": context.partition_key})
