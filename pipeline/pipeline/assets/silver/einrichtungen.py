"""Silver layer: build SCD-2 dim_einrichtung from Bronze Qualitätsberichte."""

import json

import pandas as pd
from dagster import AssetExecutionContext, Output, StaticPartitionsDefinition, asset
from sqlalchemy import text

from pipeline.resources import DatabaseResource

BERICHTSJAHRE = StaticPartitionsDefinition(["2020", "2021", "2022", "2023"])

_UPSERT_SQL = """
INSERT INTO core.dim_einrichtung (
    ik_nummer, standort_id, name, ags, versorgungsstufe,
    plz, ort, strasse, betten, valid_from, valid_to, is_current
)
SELECT
    r.ik_nummer,
    r.standort_id,
    r.name,
    r.ags,
    r.versorgungsstufe::core.versorgungsstufe_enum,
    r.plz,
    r.ort,
    r.strasse,
    r.betten::integer,
    make_date(:berichtsjahr, 1, 1) AS valid_from,
    '9999-12-31'::date             AS valid_to,
    true                           AS is_current
FROM core.staging_einrichtung r
ON CONFLICT (ik_nummer, standort_id) WHERE is_current
DO UPDATE SET
    name             = EXCLUDED.name,
    ags              = EXCLUDED.ags,
    versorgungsstufe = EXCLUDED.versorgungsstufe,
    plz              = EXCLUDED.plz,
    ort              = EXCLUDED.ort,
    strasse          = EXCLUDED.strasse,
    betten           = EXCLUDED.betten,
    valid_from       = EXCLUDED.valid_from
"""


@asset(
    group_name="silver",
    partitions_def=BERICHTSJAHRE,
    deps=["qualitaetsberichte_raw"],
    description="Normalize raw Qualitätsbericht XML into SCD-2 core.dim_einrichtung.",
)
def dim_einrichtung(context: AssetExecutionContext, database: DatabaseResource) -> Output:
    """
    Extract hospital master data from Bronze and load into core.dim_einrichtung
    using Slowly Changing Dimension Type 2 (SCD-2) semantics.

    Reads the pre-parsed JSON stored by the Bronze asset to avoid re-parsing XML.
    """
    berichtsjahr = int(context.partition_key)

    query = """
        SELECT DISTINCT ON (ik_nummer)
            parsed_json,
            ik_nummer
        FROM raw.qualitaetsbericht
        WHERE berichtsjahr = %(berichtsjahr)s AND ik_nummer IS NOT NULL
        ORDER BY ik_nummer, ingested_at DESC
    """

    with database.get_sync_session() as session:
        df = pd.read_sql(query, con=session.connection(), params={"berichtsjahr": berichtsjahr})

    records = _extract_einrichtungen(df)
    context.log.info(f"Parsed {len(records)} Einrichtung records from Bronze for {berichtsjahr}")

    upserted = 0
    if records:
        staging = pd.DataFrame(records)
        with database.get_sync_session() as session:
            staging.to_sql(
                "staging_einrichtung",
                con=session.connection(),
                schema="core",
                if_exists="replace",
                index=False,
            )
            session.execute(text(_UPSERT_SQL), {"berichtsjahr": berichtsjahr})
            upserted = len(records)

    return Output(
        value=upserted,
        metadata={"upserted_rows": upserted, "berichtsjahr": berichtsjahr},
    )


def _extract_einrichtungen(df: pd.DataFrame) -> list[dict]:
    """Extract einrichtung fields from the parsed_json column stored by the Bronze asset."""
    records = []
    for _, row in df.iterrows():
        try:
            parsed = json.loads(row["parsed_json"]) if isinstance(row["parsed_json"], str) else row["parsed_json"]
        except Exception:
            continue
        ein = parsed.get("einrichtung") or {}
        ik_nummer = ein.get("ik_nummer")
        if not ik_nummer:
            continue
        records.append({
            "ik_nummer": ik_nummer,
            "standort_id": ein.get("standort_id") or "00",
            "name": ein.get("name"),
            "ags": None,  # Not in QB XML; enriched separately via BKG geodata
            "versorgungsstufe": ein.get("versorgungsstufe"),
            "plz": ein.get("plz"),
            "ort": ein.get("ort"),
            "strasse": ein.get("strasse"),
            "betten": ein.get("betten"),
        })
    return records
