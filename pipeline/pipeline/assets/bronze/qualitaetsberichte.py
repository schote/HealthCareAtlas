"""Bronze layer: ingest and parse Strukturierte Qualitätsberichte (QB) XML from G-BA/DeQS."""

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import pandas as pd
from dagster import AssetExecutionContext, Output, StaticPartitionsDefinition, asset
from lxml import etree

from pipeline.resources import DatabaseResource

BERICHTSJAHRE = StaticPartitionsDefinition(["2020", "2021", "2022", "2023"])

# Traegerschaft code → canonical German label
_TRAEGERSCHAFT_MAP = {
    "oe": "oeffentlich",
    "öffentlich": "oeffentlich",
    "fg": "freigemeinnuetzig",
    "freigemeinnützig": "freigemeinnuetzig",
    "pr": "privat",
    "privat": "privat",
}

# Versorgungsstufe int code → canonical label
_VERSORGUNGSSTUFE_MAP = {
    "1": "Grund",
    "2": "Regel",
    "3": "Schwerpunkt",
    "4": "Maximal",
    "grundversorgung": "Grund",
    "regelversorgung": "Regel",
    "schwerpunktversorgung": "Schwerpunkt",
    "maximalversorgung": "Maximal",
}


def _local(tag: str) -> str:
    """Return lxml local-name XPath predicate to ignore namespaces."""
    return f"*[local-name()='{tag}']"


def _text(el: etree._Element | None, *path: str) -> str | None:
    """Navigate a chain of local-name child elements and return stripped text."""
    node = el
    for step in path:
        if node is None:
            return None
        results = node.xpath(f".//{_local(step)}")
        found = results[0] if results else None
        node = found
    if node is None or node.text is None:
        return None
    return node.text.strip() or None


def _float(el: etree._Element | None, *path: str) -> float | None:
    raw = _text(el, *path)
    if raw is None:
        return None
    try:
        return float(raw.replace(",", "."))
    except ValueError:
        return None


def _int(el: etree._Element | None, *path: str) -> int | None:
    raw = _text(el, *path)
    if raw is None:
        return None
    try:
        return int(float(raw.replace(",", ".")))
    except ValueError:
        return None


def _bool(el: etree._Element | None, *path: str) -> bool | None:
    raw = _text(el, *path)
    if raw is None:
        return None
    return raw.lower() in ("true", "ja", "1", "yes")


def _find_all(root: etree._Element, local_name: str) -> list[etree._Element]:
    """Find all descendant elements with a given local name (namespace-agnostic)."""
    return root.xpath(f".//*[local-name()='{local_name}']")


def parse_qb_xml(xml_content: bytes, berichtsjahr: int) -> dict[str, Any]:
    """
    Parse a Strukturierter Qualitätsbericht XML file into structured Python dicts.

    The QB XML schema has evolved across versions (2003–2023).  We use
    local-name() XPath queries throughout to remain namespace-agnostic and
    handle minor schema variations between G-BA release years.

    Returns a dict with keys: einrichtung, qualitaetsindikatoren,
    mindestmengen, fachabteilungen.
    """
    try:
        root = etree.fromstring(xml_content)
    except etree.XMLSyntaxError as exc:
        return {"error": str(exc), "einrichtung": None,
                "qualitaetsindikatoren": [], "mindestmengen": [], "fachabteilungen": []}

    result: dict[str, Any] = {
        "einrichtung": _parse_einrichtung(root, berichtsjahr),
        "qualitaetsindikatoren": _parse_qualitaetsindikatoren(root),
        "mindestmengen": _parse_mindestmengen(root),
        "fachabteilungen": _parse_fachabteilungen(root),
    }
    return result


def _parse_einrichtung(root: etree._Element, berichtsjahr: int) -> dict[str, Any]:
    """Extract hospital master data from the Einrichtung element (Kapitel A)."""
    # The Einrichtung block appears under several element names across QB versions
    ein = None
    for tag in ("Einrichtung", "Krankenhaus", "Institution"):
        candidates = _find_all(root, tag)
        if candidates:
            ein = candidates[0]
            break

    ik_nummer = _text(root, "IK") or _text(ein, "IK") or _text(root, "Institutionskennzeichen")
    standort_id = _text(root, "Standort") or _text(ein, "Standort") or "00"

    # Versorgungsstufe: can be integer (1-4) or string
    raw_vs = (_text(ein, "Versorgungsstufe") or _text(root, "Versorgungsstufe") or "").lower()
    versorgungsstufe = _VERSORGUNGSSTUFE_MAP.get(raw_vs)

    # Traegerschaft
    raw_tr = (_text(ein, "Traegerschaft") or _text(root, "Traegerschaft") or "").lower()
    traegerschaft = _TRAEGERSCHAFT_MAP.get(raw_tr)

    # Geo coordinates (added in QB 2021)
    lat = _float(ein, "Breitengrad") or _float(ein, "Latitude") or _float(root, "Breitengrad")
    lon = _float(ein, "Laengengrad") or _float(ein, "Longitude") or _float(root, "Laengengrad")

    return {
        "ik_nummer": ik_nummer,
        "standort_id": standort_id,
        "name": _text(ein, "Name") or _text(root, "Krankenhausname"),
        "plz": _text(ein, "PLZ") or _text(ein, "Postleitzahl"),
        "ort": _text(ein, "Ort") or _text(ein, "Stadt"),
        "strasse": _text(ein, "Strasse") or _text(ein, "Straße"),
        "traegerschaft": traegerschaft,
        "versorgungsstufe": versorgungsstufe,
        "betten": _int(ein, "Bettenzahl") or _int(ein, "Betten") or _int(root, "Bettenzahl"),
        "lat": lat,
        "lon": lon,
    }


def _parse_qualitaetsindikatoren(root: etree._Element) -> list[dict[str, Any]]:
    """
    Extract all quality indicator results.

    QB XML uses several element names across versions:
    - QualitaetsindikatorErgebnis (common)
    - Qualitaetsindikator
    - QI_Ergebnis
    """
    indicators = []
    seen = set()

    for tag in ("QualitaetsindikatorErgebnis", "Qualitaetsindikator", "QI_Ergebnis", "Ergebnis"):
        for el in _find_all(root, tag):
            kennzahl_id = (
                _text(el, "KennzahlID")
                or _text(el, "Kennzahl")
                or _text(el, "QI_ID")
                or _text(el, "IndikatorID")
            )
            if not kennzahl_id:
                continue
            # Deduplicate by kennzahl_id
            if kennzahl_id in seen:
                continue
            seen.add(kennzahl_id)

            indicators.append({
                "kennzahl_id": kennzahl_id,
                "leistungsbereich": (
                    _text(el, "Leistungsbereich")
                    or _text(el, "Bereich")
                    or _text(el, "Themenbereich")
                ),
                "bezeichnung": (
                    _text(el, "Bezeichnung")
                    or _text(el, "Name")
                    or _text(el, "Indikatorbezeichnung")
                ),
                "zaehler": _int(el, "Zaehler") or _int(el, "Zähler"),
                "nenner": _int(el, "Nenner"),
                "ergebnis": _float(el, "Ergebnis") or _float(el, "Wert"),
                "referenzbereich_von": (
                    _float(el, "ReferenzbereichUntereGrenze")
                    or _float(el, "Referenzbereich_von")
                    or _float(el, "UntereGrenze")
                ),
                "referenzbereich_bis": (
                    _float(el, "ReferenzbereichObereGrenze")
                    or _float(el, "Referenzbereich_bis")
                    or _float(el, "ObereGrenze")
                ),
                "auffaellig": (
                    _bool(el, "Auffaelligkeitskriterium")
                    or _bool(el, "Auffaelligkeit")
                    or _bool(el, "Auffaellig")
                ),
                "ist_planungsrelevant": (
                    _bool(el, "IstPlanungsrelevant")
                    or _bool(el, "Planungsrelevant")
                ),
            })

    return indicators


def _parse_mindestmengen(root: etree._Element) -> list[dict[str, Any]]:
    """Extract minimum volume (Mindestmenge) requirements."""
    result = []
    for el in _find_all(root, "Mindestmenge"):
        ops_code = _text(el, "OPSCode") or _text(el, "OPS") or _text(el, "Leistung")
        if not ops_code:
            continue

        raw_status = _text(el, "Status") or ""
        ausnahme = _text(el, "Ausnahmetatbestand") or _text(el, "Ausnahme")

        result.append({
            "ops_code": ops_code,
            "soll": _int(el, "Soll") or _int(el, "Mindestzahl"),
            "ist": _int(el, "Ist") or _int(el, "Fallzahl"),
            "status": {
                "konform": raw_status.lower() in ("erfuellt", "erfüllt", "ja", "true"),
                "status_text": raw_status,
                "ausnahme": ausnahme,
            },
        })

    return result


def _parse_fachabteilungen(root: etree._Element) -> list[dict[str, Any]]:
    """Extract department (Fachabteilung) master data."""
    result = []
    for el in _find_all(root, "Fachabteilung"):
        fab_schluessel = (
            _text(el, "FABSchluessel")
            or _text(el, "Abteilungsschluessel")
            or _text(el, "Schluessel")
        )
        if not fab_schluessel:
            continue
        result.append({
            "fab_schluessel": fab_schluessel,
            "bezeichnung": _text(el, "FABBezeichnung") or _text(el, "Bezeichnung"),
            "betten": _int(el, "Bettenzahl") or _int(el, "Betten"),
            "fallzahl": _int(el, "Fallzahl") or _int(el, "Faelle"),
        })

    return result


@asset(
    group_name="bronze",
    partitions_def=BERICHTSJAHRE,
    description="Parse Qualitätsbericht XML → structured rows in raw.qualitaetsbericht.",
)
def qualitaetsberichte_raw(context: AssetExecutionContext, database: DatabaseResource) -> Output:
    """
    Bronze asset: ingest and parse annual QB XML files.

    Stores both the raw XML (for full auditability) and a parsed JSON summary
    so Silver assets can read structured data without re-parsing.

    Data source: G-BA/DeQS ZIP archives, extracted to data/raw/qb/<berichtsjahr>/.
    """
    berichtsjahr = int(context.partition_key)
    data_dir = Path("/data/raw/qb") / str(berichtsjahr)

    xml_files = sorted(data_dir.glob("*.xml")) if data_dir.exists() else []
    context.log.info(f"Found {len(xml_files)} QB XML files for {berichtsjahr}")

    rows: list[dict] = []
    parse_errors = 0

    for xml_file in xml_files:
        content = xml_file.read_bytes()
        file_hash = hashlib.sha256(content).hexdigest()

        parsed = parse_qb_xml(content, berichtsjahr)
        if "error" in parsed:
            context.log.warning(f"Parse error in {xml_file.name}: {parsed['error']}")
            parse_errors += 1

        ein = parsed.get("einrichtung") or {}
        rows.append({
            "berichtsjahr": berichtsjahr,
            "source_file": xml_file.name,
            "file_hash": file_hash,
            "ik_nummer": ein.get("ik_nummer"),
            "raw_xml": content.decode("utf-8", errors="replace"),
            "parsed_json": json.dumps(parsed, ensure_ascii=False, default=str),
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
                chunksize=50,
            )

    context.log.info(
        f"Ingested {row_count} QB records for {berichtsjahr} "
        f"({parse_errors} parse errors)"
    )
    return Output(
        value=row_count,
        metadata={
            "row_count": row_count,
            "parse_errors": parse_errors,
            "berichtsjahr": berichtsjahr,
        },
    )
