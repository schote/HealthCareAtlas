"""Quality indicators router for Versorgungsatlas API."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_session

# Catalog endpoint: GET /indicators
router = APIRouter(prefix="/indicators", tags=["indicators"])

# Hospital extension: GET /hospitals/{ik}/indicators
hospitals_indicators_router = APIRouter(prefix="/hospitals", tags=["hospitals"])


# ── Pydantic schemas ──────────────────────────────────────────────────────


class QualitaetsindikatorCatalog(BaseModel):
    kennzahl_id: str
    bezeichnung: str | None
    leistungsbereich: str | None
    rechenregel: str | None
    datenquelle: str | None


class QualitaetsindikatorResult(BaseModel):
    kennzahl_id: str | None
    bezeichnung: str | None
    leistungsbereich: str | None
    zaehler: int | None
    nenner: int | None
    ergebnis: float | None
    referenzbereich_von: float | None
    referenzbereich_bis: float | None
    auffaellig: bool | None
    ist_planungsrelevant: bool | None


class LeistungsbereichGroup(BaseModel):
    leistungsbereich: str | None
    indikatoren: list[QualitaetsindikatorResult]


class HospitalIndicatorsResponse(BaseModel):
    ik_nummer: str
    berichtsjahr: int
    gruppen: list[LeistungsbereichGroup]


# ── Endpoints ─────────────────────────────────────────────────────────────


@hospitals_indicators_router.get("/{ik}/indicators", response_model=HospitalIndicatorsResponse)
async def get_hospital_indicators(
    ik: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    berichtsjahr: int = Query(default=2022, description="Reporting year"),
) -> HospitalIndicatorsResponse:
    """Return quality indicators for a hospital grouped by Leistungsbereich."""
    rows = await session.execute(
        text("""
            SELECT
                fqi.kennzahl_id,
                COALESCE(fqi.bezeichnung, dqi.bezeichnung) AS bezeichnung,
                COALESCE(fqi.leistungsbereich, dqi.leistungsbereich) AS leistungsbereich,
                fqi.zaehler,
                fqi.nenner,
                fqi.ergebnis,
                fqi.referenzbereich_von,
                fqi.referenzbereich_bis,
                fqi.auffaellig,
                fqi.ist_planungsrelevant
            FROM core.fact_qualitaetsindikator fqi
            LEFT JOIN core.dim_qualitaetsindikator dqi ON dqi.kennzahl_id = fqi.kennzahl_id
            WHERE fqi.ik_nummer = :ik AND fqi.berichtsjahr = :berichtsjahr
            ORDER BY COALESCE(fqi.leistungsbereich, dqi.leistungsbereich), fqi.kennzahl_id
        """),
        {"ik": ik, "berichtsjahr": berichtsjahr},
    )

    data = rows.mappings().fetchall()

    # Group by Leistungsbereich
    groups: dict[str | None, list[QualitaetsindikatorResult]] = {}
    for row in data:
        lb = row["leistungsbereich"]
        groups.setdefault(lb, [])
        groups[lb].append(
            QualitaetsindikatorResult(
                kennzahl_id=row["kennzahl_id"],
                bezeichnung=row["bezeichnung"],
                leistungsbereich=lb,
                zaehler=row["zaehler"],
                nenner=row["nenner"],
                ergebnis=float(row["ergebnis"]) if row["ergebnis"] is not None else None,
                referenzbereich_von=float(row["referenzbereich_von"]) if row["referenzbereich_von"] is not None else None,
                referenzbereich_bis=float(row["referenzbereich_bis"]) if row["referenzbereich_bis"] is not None else None,
                auffaellig=row["auffaellig"],
                ist_planungsrelevant=row["ist_planungsrelevant"],
            )
        )

    gruppen = [
        LeistungsbereichGroup(leistungsbereich=lb, indikatoren=inds)
        for lb, inds in groups.items()
    ]

    return HospitalIndicatorsResponse(
        ik_nummer=ik,
        berichtsjahr=berichtsjahr,
        gruppen=gruppen,
    )


@router.get("", response_model=list[QualitaetsindikatorCatalog])
async def list_indicators(
    session: Annotated[AsyncSession, Depends(get_session)],
    leistungsbereich: str | None = Query(default=None, description="Filter by Leistungsbereich"),
) -> list[QualitaetsindikatorCatalog]:
    """Return the quality indicator catalog (dim_qualitaetsindikator)."""
    where = "WHERE leistungsbereich = :leistungsbereich" if leistungsbereich else ""
    params: dict = {}
    if leistungsbereich:
        params["leistungsbereich"] = leistungsbereich

    rows = await session.execute(
        text(f"""
            SELECT kennzahl_id, bezeichnung, leistungsbereich, rechenregel, datenquelle
            FROM core.dim_qualitaetsindikator
            {where}
            ORDER BY leistungsbereich, kennzahl_id
        """),
        params,
    )

    return [
        QualitaetsindikatorCatalog(
            kennzahl_id=row["kennzahl_id"],
            bezeichnung=row["bezeichnung"],
            leistungsbereich=row["leistungsbereich"],
            rechenregel=row["rechenregel"],
            datenquelle=row["datenquelle"],
        )
        for row in rows.mappings()
    ]
