"""Silver layer: extract quality indicators from Bronze QB XML into core fact/dim tables."""

import pandas as pd
from dagster import AssetExecutionContext, Output, StaticPartitionsDefinition, asset
from sqlalchemy import text

from pipeline.resources import DatabaseResource
from pipeline.pipeline.assets.bronze.qualitaetsberichte import parse_qb_xml

BERICHTSJAHRE = StaticPartitionsDefinition(["2020", "2021", "2022", "2023"])

_UPSERT_INDIKATOR_SQL = """
INSERT INTO core.dim_qualitaetsindikator (kennzahl_id, bezeichnung, leistungsbereich)
VALUES (:kennzahl_id, :bezeichnung, :leistungsbereich)
ON CONFLICT (kennzahl_id) DO UPDATE SET
    bezeichnung      = COALESCE(EXCLUDED.bezeichnung, core.dim_qualitaetsindikator.bezeichnung),
    leistungsbereich = COALESCE(EXCLUDED.leistungsbereich, core.dim_qualitaetsindikator.leistungsbereich)
"""

_UPSERT_EINRICHTUNG_SQL = """
INSERT INTO core.dim_einrichtung (
    ik_nummer, standort_id, name, plz, ort, strasse, betten,
    versorgungsstufe, traegerschaft, lat, lon,
    valid_from, valid_to, is_current
)
VALUES (
    :ik_nummer, :standort_id, :name, :plz, :ort, :strasse, :betten,
    :versorgungsstufe::core.versorgungsstufe_enum,
    :traegerschaft::core.traegerschaft_enum,
    :lat, :lon,
    make_date(:berichtsjahr, 1, 1), '9999-12-31'::date, true
)
ON CONFLICT (ik_nummer, standort_id) WHERE is_current
DO UPDATE SET
    name          = COALESCE(EXCLUDED.name, core.dim_einrichtung.name),
    traegerschaft = COALESCE(EXCLUDED.traegerschaft, core.dim_einrichtung.traegerschaft),
    lat           = COALESCE(EXCLUDED.lat, core.dim_einrichtung.lat),
    lon           = COALESCE(EXCLUDED.lon, core.dim_einrichtung.lon),
    betten        = COALESCE(EXCLUDED.betten, core.dim_einrichtung.betten),
    valid_from    = EXCLUDED.valid_from
"""


@asset(
    group_name="silver",
    partitions_def=BERICHTSJAHRE,
    deps=["qualitaetsberichte_raw"],
    description="Extract QB quality indicators from Bronze into core.fact_qualitaetsindikator and core.dim_qualitaetsindikator.",
    required_resource_keys={"database"},
)
def qualitaetsindikatoren(context: AssetExecutionContext, database: DatabaseResource) -> Output:
    """
    Read raw QB XML from Bronze, parse it, and load quality indicators into:
    - core.dim_qualitaetsindikator (upsert, dedup by kennzahl_id)
    - core.fact_qualitaetsindikator (bulk insert)
    - core.dim_einrichtung (upsert lat/lon/traegerschaft)
    """
    berichtsjahr = int(context.partition_key)

    query = """
        SELECT id, raw_xml, source_file
        FROM raw.qualitaetsbericht
        WHERE berichtsjahr = %(berichtsjahr)s
    """

    with database.get_sync_session() as session:
        df = pd.read_sql(query, con=session.connection(), params={"berichtsjahr": berichtsjahr})

    context.log.info(f"Found {len(df)} QB records for {berichtsjahr} in Bronze")

    all_indicators: list[dict] = []
    seen_kennzahl_ids: set[str] = set()
    dim_indicators: list[dict] = []
    einrichtung_updates: list[dict] = []

    for _, row in df.iterrows():
        try:
            parsed = parse_qb_xml(row["raw_xml"].encode("utf-8") if isinstance(row["raw_xml"], str) else row["raw_xml"], berichtsjahr)
        except Exception as exc:
            context.log.warning(f"Failed to parse {row['source_file']}: {exc}")
            continue

        einrichtung = parsed.get("einrichtung") or {}
        ik_nummer = einrichtung.get("ik_nummer")
        if not ik_nummer:
            continue

        einrichtung_updates.append({
            "ik_nummer": ik_nummer,
            "standort_id": einrichtung.get("standort_id", "00"),
            "name": einrichtung.get("name"),
            "plz": einrichtung.get("plz"),
            "ort": einrichtung.get("ort"),
            "strasse": einrichtung.get("strasse"),
            "betten": einrichtung.get("betten"),
            "versorgungsstufe": einrichtung.get("versorgungsstufe"),
            "traegerschaft": einrichtung.get("traegerschaft"),
            "lat": einrichtung.get("lat"),
            "lon": einrichtung.get("lon"),
            "berichtsjahr": berichtsjahr,
        })

        for qi in parsed.get("qualitaetsindikatoren", []):
            kennzahl_id = qi.get("kennzahl_id")
            if not kennzahl_id:
                continue

            if kennzahl_id not in seen_kennzahl_ids:
                seen_kennzahl_ids.add(kennzahl_id)
                dim_indicators.append({
                    "kennzahl_id": kennzahl_id,
                    "bezeichnung": qi.get("bezeichnung"),
                    "leistungsbereich": qi.get("leistungsbereich"),
                })

            all_indicators.append({
                "ik_nummer": ik_nummer,
                "berichtsjahr": berichtsjahr,
                "kennzahl_id": kennzahl_id,
                "leistungsbereich": qi.get("leistungsbereich"),
                "bezeichnung": qi.get("bezeichnung"),
                "zaehler": qi.get("zaehler"),
                "nenner": qi.get("nenner"),
                "ergebnis": qi.get("ergebnis"),
                "referenzbereich_von": qi.get("referenzbereich_von"),
                "referenzbereich_bis": qi.get("referenzbereich_bis"),
                "auffaellig": qi.get("auffaellig"),
                "ist_planungsrelevant": qi.get("ist_planungsrelevant"),
            })

    context.log.info(
        f"Parsed {len(einrichtung_updates)} einrichtungen, "
        f"{len(dim_indicators)} unique indicators, "
        f"{len(all_indicators)} fact rows for {berichtsjahr}"
    )

    with database.get_sync_session() as session:
        conn = session.connection()

        for dim_row in dim_indicators:
            session.execute(text(_UPSERT_INDIKATOR_SQL), dim_row)

        for e_row in einrichtung_updates:
            try:
                session.execute(text(_UPSERT_EINRICHTUNG_SQL), e_row)
            except Exception as exc:
                context.log.warning(f"Einrichtung upsert failed for {e_row['ik_nummer']}: {exc}")

        if all_indicators:
            fact_df = pd.DataFrame(all_indicators)
            fact_df.to_sql(
                "fact_qualitaetsindikator",
                con=conn,
                schema="core",
                if_exists="append",
                index=False,
                method="multi",
                chunksize=500,
            )

        session.commit()

    return Output(
        value=len(all_indicators),
        metadata={
            "fact_rows": len(all_indicators),
            "dim_rows": len(dim_indicators),
            "einrichtung_updates": len(einrichtung_updates),
            "berichtsjahr": berichtsjahr,
        },
    )
