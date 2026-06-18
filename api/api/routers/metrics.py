from fastapi import APIRouter

from api.schemas import MetricDefinition

router = APIRouter(prefix="/metrics", tags=["metrics"])

METRICS: list[MetricDefinition] = [
    MetricDefinition(
        key="def_index",
        label="Deficit Index",
        description="Composite deficit index (0-100, higher = more deficit).",
        unit="score",
        weight=1.0,
        source="Versorgungsatlas fusion pipeline",
    ),
    MetricDefinition(
        key="quality",
        label="Qualitaetsdefizit (QB)",
        description="Fraction of quality indicators flagged as auffaellig in Strukturierte Qualitaetsberichte (0-1, higher = worse).",
        unit="ratio",
        weight=0.70,
        source="Strukturierte Qualitaetsberichte (G-BA/DeQS)",
    ),
    MetricDefinition(
        key="casemix",
        label="Casemix-Index (DRG)",
        description="Average DRG casemix index. Lower values indicate less specialisation and higher supply deficit.",
        unit="index",
        weight=0.30,
        source="Paragraph 21-Daten (InEK / FDZ)",
    ),
]


@router.get("", response_model=list[MetricDefinition])
async def list_metrics() -> list[MetricDefinition]:
    """Return all metric definitions with labels, descriptions, units, and weights."""
    return METRICS
