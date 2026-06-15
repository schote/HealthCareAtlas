from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_session
from api.schemas import Region, RegionDetail

router = APIRouter(prefix="/regions", tags=["regions"])


@router.get("", response_model=list[Region])
async def list_regions(
    session: Annotated[AsyncSession, Depends(get_session)],
    ebene: str | None = None,
) -> list[Region]:
    """List all regions, optionally filtered by administrative level."""
    params: dict = {}
    where = ""
    if ebene:
        where = "WHERE ebene = :ebene"
        params["ebene"] = ebene

    rows = await session.execute(
        text(f"SELECT * FROM core.dim_region {where} ORDER BY ags"),
        params,
    )
    return [Region(**dict(r)) for r in rows.mappings()]


@router.get("/{ags}", response_model=RegionDetail)
async def get_region(
    ags: str,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> RegionDetail:
    """Get a region with its child regions."""
    row = await session.execute(
        text("SELECT * FROM core.dim_region WHERE ags = :ags"),
        {"ags": ags},
    )
    data = row.mappings().fetchone()
    if data is None:
        raise HTTPException(status_code=404, detail=f"Region {ags!r} not found")

    children_rows = await session.execute(
        text("SELECT * FROM core.dim_region WHERE parent_ags = :ags ORDER BY ags"),
        {"ags": ags},
    )
    children = [Region(**dict(r)) for r in children_rows.mappings()]

    return RegionDetail(**dict(data), children=children)
