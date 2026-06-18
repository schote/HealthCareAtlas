from fastapi import APIRouter

from api.schemas import MetricDefinition

router = APIRouter(prefix="/metrics", tags=["metrics"])

METRICS: list[MetricDefinition] = [
    MetricDefinition(
        key="def_index",
        label="Deficit Index",
        description="Supply deficit index (0-100, higher = more deficit). Based on Mindestmenge compliance.",
        unit="score",
        weight=1.0,
        source="Versorgungsatlas fusion pipeline",
    ),
    MetricDefinition(
        key="quality",
        label="Mindestmenge-Defizit",
        description="Fraction of mandatory minimum-volume procedures for which the hospital is NOT authorized (0=fully compliant, 1=none met).",
        unit="ratio",
        weight=1.0,
        source="Strukturierte Qualitaetsberichte (G-BA) — Mindestmengen",
    ),
]


@router.get("", response_model=list[MetricDefinition])
async def list_metrics() -> list[MetricDefinition]:
    """Return all metric definitions with labels, descriptions, units, and weights."""
    return METRICS
