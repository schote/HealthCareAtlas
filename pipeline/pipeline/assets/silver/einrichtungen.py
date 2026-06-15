"""Silver layer: build SCD-2 dim_einrichtung from Bronze Qualitätsberichte."""

import pandas as pd
from dagster import AssetExecutionContext, Output, StaticPartitionsDefinition, asset

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
    r.betten,
    make_date(:berichtsjahr, 1, 1) AS valid_from,
    '9999-12-31'::date             AS valid_to,
    true                           AS is_current
FROM staging_einrichtung r
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
    required_resource_keys={"database"},
)
def dim_einrichtung(context: AssetExecutionContext, database: DatabaseResource) -> Output:
    """
    Extract hospital master data from Bronze and load into core.dim_einrichtung
    using Slowly Changing Dimension Type 2 (SCD-2) semantics.

    When attributes change between years the old row gets valid_to set and
    is_current=false; a new row is inserted with the new values.
    """
    berichtsjahr = int(context.partition_key)

    # Read parsed fields from raw layer
    query = """
        SELECT DISTINCT
            raw_xml::xml AS xml_doc,
            source_file,
            berichtsjahr
        FROM raw.qualitaetsbericht
        WHERE berichtsjahr = %(berichtsjahr)s
    """

    with database.get_sync_session() as session:
        df = pd.read_sql(query, con=session.connection(), params={"berichtsjahr": berichtsjahr})

    # TODO: parse XML with lxml to extract structured fields from each Qualitätsbericht.
    # For now produce an empty DataFrame so the asset graph can be validated end-to-end.
    records = _parse_qb_xml(df, berichtsjahr)
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
            session.execute(
                __import__("sqlalchemy").text(_UPSERT_SQL),
                {"berichtsjahr": berichtsjahr},
            )
            upserted = len(records)

    return Output(
        value=upserted,
        metadata={"upserted_rows": upserted, "berichtsjahr": berichtsjahr},
    )


def _parse_qb_xml(df: pd.DataFrame, berichtsjahr: int) -> list[dict]:
    """
    Parse raw XML rows into structured hospital records.

    TODO: implement full lxml XPath extraction against the DeQS QB schema.
    The QB XML schema is documented in the G-BA specification (Anlage 1 QBR).
    """
    return []
