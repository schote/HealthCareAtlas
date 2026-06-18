from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_session
from api.schemas import HospitalDetail, HospitalList

router = APIRouter(prefix="/hospitals", tags=["hospitals"])


@router.get("", response_model=HospitalList)
async def list_hospitals(
    session: Annotated[AsyncSession, Depends(get_session)],
    berichtsjahr: int = Query(default=2022, description="Reporting year"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
    search: str | None = Query(default=None, description="Search by name or IK number"),
    min_def_index: float | None = Query(default=None, ge=0, le=100),
    max_def_index: float | None = Query(default=None, ge=0, le=100),
    versorgungsstufe: str | None = Query(default=None),
) -> HospitalList:
    """List hospitals with their KPIs. Reads exclusively from mart schema."""
    where_clauses = ["e.is_current = TRUE"]
    params: dict = {"berichtsjahr": berichtsjahr, "offset": (page - 1) * page_size, "limit": page_size}

    if search:
        where_clauses.append("(e.name ILIKE :search OR e.ik_nummer ILIKE :search)")
        params["search"] = f"%{search}%"
    if min_def_index is not None:
        where_clauses.append("k.def_index >= :min_def_index")
        params["min_def_index"] = min_def_index
    if max_def_index is not None:
        where_clauses.append("k.def_index <= :max_def_index")
        params["max_def_index"] = max_def_index
    if versorgungsstufe:
        where_clauses.append("e.versorgungsstufe = :versorgungsstufe")
        params["versorgungsstufe"] = versorgungsstufe

    where_sql = " AND ".join(where_clauses)

    count_result = await session.execute(
        text(f"""
            SELECT COUNT(*) FROM core.dim_einrichtung e
            LEFT JOIN mart.einrichtung_kpi k
                ON k.ik_nummer = e.ik_nummer AND k.berichtsjahr = :berichtsjahr
            WHERE {where_sql}
        """),
        params,
    )
    total = count_result.scalar() or 0

    rows = await session.execute(
        text(f"""
            SELECT
                e.ik_nummer, e.name, e.ort, e.plz, e.ags,
                e.versorgungsstufe::text,
                k.berichtsjahr, k.def_index, k.quality_score, k.casemix_index,
                k.konfidenz, k.datenstand
            FROM core.dim_einrichtung e
            LEFT JOIN mart.einrichtung_kpi k
                ON k.ik_nummer = e.ik_nummer AND k.berichtsjahr = :berichtsjahr
            WHERE {where_sql}
            ORDER BY k.def_index DESC NULLS LAST
            LIMIT :limit OFFSET :offset
        """),
        params,
    )

    items = []
    for row in rows.mappings():
        kpi = None
        if row["berichtsjahr"] is not None:
            kpi = {
                "berichtsjahr": row["berichtsjahr"],
                "def_index": row["def_index"],
                "quality_score": row["quality_score"],
                "casemix_index": row["casemix_index"],
                "konfidenz": row["konfidenz"],
                "datenstand": row["datenstand"],
            }
        items.append({
            "ik_nummer": row["ik_nummer"],
            "name": row["name"],
            "ort": row["ort"],
            "plz": row["plz"],
            "ags": row["ags"],
            "versorgungsstufe": row["versorgungsstufe"],
            "kpi": kpi,
        })

    return HospitalList(total=total, items=items, page=page, page_size=page_size)


@router.get("/{ik}", response_model=HospitalDetail)
async def get_hospital(
    ik: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    berichtsjahr: int = Query(default=2022),
) -> HospitalDetail:
    """Get a single hospital with KPI detail."""
    row = await session.execute(
        text("""
            SELECT
                e.ik_nummer, e.standort_id, e.name, e.ort, e.plz, e.ags,
                e.strasse, e.versorgungsstufe::text,
                k.berichtsjahr, k.def_index, k.quality_score, k.casemix_index,
                k.konfidenz, k.datenstand
            FROM core.dim_einrichtung e
            LEFT JOIN mart.einrichtung_kpi k
                ON k.ik_nummer = e.ik_nummer AND k.berichtsjahr = :berichtsjahr
            WHERE e.ik_nummer = :ik AND e.is_current
            LIMIT 1
        """),
        {"ik": ik, "berichtsjahr": berichtsjahr},
    )
    data = row.mappings().fetchone()
    if data is None:
        raise HTTPException(status_code=404, detail=f"Hospital {ik!r} not found")

    kpi = None
    if data["berichtsjahr"] is not None:
        kpi = {
            "berichtsjahr": data["berichtsjahr"],
            "def_index": data["def_index"],
            "quality_score": data["quality_score"],
            "casemix_index": data["casemix_index"],
            "konfidenz": data["konfidenz"],
            "datenstand": data["datenstand"],
        }

    return HospitalDetail(
        ik_nummer=data["ik_nummer"],
        standort_id=data["standort_id"],
        name=data["name"],
        ort=data["ort"],
        plz=data["plz"],
        ags=data["ags"],
        strasse=data["strasse"],
        versorgungsstufe=data["versorgungsstufe"],
        kpi=kpi,
    )
