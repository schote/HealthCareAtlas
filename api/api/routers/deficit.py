from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_session
from api.schemas import DeficitRanking, DeficitRankingItem

router = APIRouter(prefix="/deficit", tags=["deficit"])


@router.get("/ranking", response_model=DeficitRanking)
async def get_deficit_ranking(
    session: Annotated[AsyncSession, Depends(get_session)],
    berichtsjahr: int = Query(default=2022),
    ebene: str = Query(default="einrichtung", description="Aggregation level"),
    metric_key: str = Query(default="def_index"),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> DeficitRanking:
    """
    Return pre-ranked deficit scores from mart.v_deficit_rank.

    The materialized view is refreshed by the Dagster gold_fusion job at the
    end of each pipeline run via REFRESH MATERIALIZED VIEW CONCURRENTLY.
    """
    try:
        count_result = await session.execute(
            text("""
                SELECT COUNT(*) FROM mart.v_deficit_rank
                WHERE berichtsjahr = :year AND ebene = :ebene AND metric_key = :metric_key
            """),
            {"year": berichtsjahr, "ebene": ebene, "metric_key": metric_key},
        )
        total = count_result.scalar() or 0

        rows = await session.execute(
            text("""
                SELECT rang, entity_id, name, ebene, metric_key, score, berichtsjahr
                FROM mart.v_deficit_rank
                WHERE berichtsjahr = :year AND ebene = :ebene AND metric_key = :metric_key
                ORDER BY rang ASC
                LIMIT :limit OFFSET :offset
            """),
            {"year": berichtsjahr, "ebene": ebene, "metric_key": metric_key,
             "limit": limit, "offset": offset},
        )
        items = [DeficitRankingItem(**dict(r)) for r in rows.mappings()]
    except DBAPIError:
        # View exists but has not been populated yet (no pipeline run)
        total = 0
        items = []

    return DeficitRanking(total=total, berichtsjahr=berichtsjahr, items=items)
