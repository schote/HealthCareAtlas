"""Bronze layer: ingest raw Strukturierte Qualitätsberichte (XML) from G-BA/DeQS."""

import hashlib
from pathlib import Path

import pandas as pd
from dagster import AssetExecutionContext, Output, StaticPartitionsDefinition, asset

from pipeline.resources import DatabaseResource

# Annual partition: one run per Berichtsjahr
BERICHTSJAHRE = StaticPartitionsDefinition(["2020", "2021", "2022", "2023"])


@asset(
    group_name="bronze",
    partitions_def=BERICHTSJAHRE,
    description="Raw Strukturierte Qualitätsberichte XML → raw.qualitaetsbericht rows (append-only).",
    required_resource_keys={"database"},
)
def qualitaetsberichte_raw(context: AssetExecutionContext, database: DatabaseResource) -> Output:
    """
    Ingest annual Qualitätsbericht XML files into the Bronze (raw) layer.

    Each run appends for one Berichtsjahr partition.  The raw records are
    stored verbatim — no transformation happens here.

    Data source: G-BA / DeQS (Gemeinsamer Bundesausschuss / Datenerhebung
    nach § 137a SGB V).  Files are placed under data/raw/qb/<berichtsjahr>/.
    """
    berichtsjahr = int(context.partition_key)
    data_dir = Path("/data/raw/qb") / str(berichtsjahr)

    # Collect XML files for this partition
    xml_files = sorted(data_dir.glob("*.xml")) if data_dir.exists() else []
    context.log.info(f"Found {len(xml_files)} XML files for {berichtsjahr} in {data_dir}")

    rows: list[dict] = []
    for xml_file in xml_files:
        content = xml_file.read_bytes()
        file_hash = hashlib.sha256(content).hexdigest()
        # TODO: parse XML with lxml to extract ik_nummer, standort_id, fab sections
        rows.append({
            "berichtsjahr": berichtsjahr,
            "source_file": xml_file.name,
            "file_hash": file_hash,
            "raw_xml": content.decode("utf-8", errors="replace"),
            "ingested_at": pd.Timestamp.utcnow(),
        })

    row_count = len(rows)
    if rows:
        df = pd.DataFrame(rows)
        with database.get_sync_session() as session:
            df.to_sql(
                "qualitaetsbericht",
                con=session.connection(),
                schema="raw",
                if_exists="append",
                index=False,
                method="multi",
            )

    context.log.info(f"Ingested {row_count} raw Qualitätsbericht records for {berichtsjahr}")
    return Output(value=row_count, metadata={"row_count": row_count, "berichtsjahr": berichtsjahr})
