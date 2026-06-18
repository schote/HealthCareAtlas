"""Silver layer: extract Mindestmenge compliance from Bronze QB XML."""

import json

import pandas as pd
from dagster import AssetExecutionContext, Output, StaticPartitionsDefinition, asset
from lxml import etree
from sqlalchemy import text

from pipeline.resources import DatabaseResource

BERICHTSJAHRE = StaticPartitionsDefinition(["2020", "2021", "2022", "2023"])


@asset(
    group_name="silver",
    partitions_def=BERICHTSJAHRE,
    deps=["qualitaetsberichte_raw"],
    description="Parse Mindestmenge authorization from QB XML into core.fact_mindestmenge.",
)
def mindestmengen(context: AssetExecutionContext, database: DatabaseResource) -> Output:
    """
    Read raw QB XML from Bronze, parse each hospital's Mindestmenge entries, and
    load into core.fact_mindestmenge.  One row per hospital × MM procedure.

    The key field is status->>'authorized' (boolean): whether the hospital is
    authorized for that procedure in the following year based on reported case volume.
    """
    berichtsjahr = int(context.partition_key)

    with database.get_sync_session() as session:
        df = pd.read_sql(
            "SELECT ik_nummer, raw_xml FROM raw.qualitaetsbericht "
            "WHERE berichtsjahr = %(year)s AND ik_nummer IS NOT NULL",
            con=session.connection(),
            params={"year": berichtsjahr},
        )

    context.log.info(f"Processing {len(df)} QB records for {berichtsjahr}")

    rows: list[dict] = []
    for _, row in df.iterrows():
        ik = row["ik_nummer"]
        xml_bytes = row["raw_xml"].encode("utf-8") if isinstance(row["raw_xml"], str) else row["raw_xml"]
        for entry in _parse_mm(xml_bytes):
            rows.append({"ik_nummer": ik, "berichtsjahr": berichtsjahr, **entry})

    context.log.info(f"Parsed {len(rows)} Mindestmenge rows for {berichtsjahr}")

    if not rows:
        context.log.warning("No Mindestmenge entries found — QB files may not include MM data")
        return Output(value=0, metadata={"inserted_rows": 0, "berichtsjahr": berichtsjahr})

    fact_df = pd.DataFrame(rows)
    fact_df["status"] = fact_df["status"].apply(json.dumps)

    with database.get_sync_session() as session:
        session.execute(
            text("DELETE FROM core.fact_mindestmenge WHERE berichtsjahr = :year"),
            {"year": berichtsjahr},
        )
        fact_df[["ik_nummer", "berichtsjahr", "ops_code", "ist", "soll", "status"]].to_sql(
            "fact_mindestmenge",
            con=session.connection(),
            schema="core",
            if_exists="append",
            index=False,
            method="multi",
            chunksize=1000,
        )

    context.log.info(f"Loaded {len(rows)} rows into fact_mindestmenge for {berichtsjahr}")
    return Output(value=len(rows), metadata={"inserted_rows": len(rows), "berichtsjahr": berichtsjahr})


def _parse_mm(xml_bytes: bytes) -> list[dict]:
    try:
        root = etree.fromstring(xml_bytes)
    except etree.XMLSyntaxError:
        return []

    rows = []
    for mm in root.xpath(".//*[local-name()='Mindestmengen']"):
        prognose = mm.xpath("*[local-name()='Mindestmengen_Angabe_Prognosejahr']")

        if prognose:
            for lb in prognose[0].xpath("*[local-name()='Leistungsbereich']"):
                bezeichnung = _txt(lb, "Bezeichnung")
                if not bezeichnung:
                    continue
                berechtigung = (_txt(lb, "Leistungsberechtigung_Prognosejahr") or "").lower()
                authorized = berechtigung in ("ja", "yes", "true", "1")

                menge = None
                for ep in lb.xpath("*[local-name()='Ergebnis_Prognosepruefung_Landesverbaende']"):
                    raw = _txt(ep, "Leistungsmenge_Berichtsjahr")
                    menge = int(raw) if raw and raw.strip().isdigit() else None
                    break

                rows.append({
                    "ops_code": bezeichnung,
                    "ist": menge,
                    "soll": None,
                    "status": {"authorized": authorized, "berechtigung": berechtigung},
                })
        else:
            # Fallback: no prognosis block — use direct Leistungsbereich (no auth data)
            for lb in mm.xpath("*[local-name()='Leistungsbereich']"):
                bezeichnung = _txt(lb, "Bezeichnung")
                if not bezeichnung:
                    continue
                mm_key = None
                for beg in lb.xpath("*[local-name()='Begruendung']"):
                    mm_key = _txt(beg, "MM_Schluessel")
                    break
                raw = _txt(lb, "Erbrachte_Menge")
                rows.append({
                    "ops_code": mm_key or bezeichnung,
                    "ist": int(raw) if raw and raw.strip().isdigit() else None,
                    "soll": None,
                    "status": {"authorized": None, "berechtigung": None},
                })

    return rows


def _txt(el: etree._Element, local_name: str) -> str | None:
    els = el.xpath(f"*[local-name()='{local_name}']")
    return els[0].text.strip() if els and els[0].text else None
