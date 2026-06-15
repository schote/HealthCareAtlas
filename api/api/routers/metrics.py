from fastapi import APIRouter

from api.schemas import MetricDefinition

router = APIRouter(prefix="/metrics", tags=["metrics"])

METRICS: list[MetricDefinition] = [
    MetricDefinition(
        key="def_index",
        label="Deficit Index",
        description="Composite deficit index (0–100, higher = more deficit).",
        unit="score",
        weight=1.0,
        source="Versorgungsatlas fusion pipeline",
    ),
    MetricDefinition(
        key="mort_adj",
        label="Adjustierte Mortalität (SMR)",
        description="Risk-adjusted standardized mortality ratio.",
        unit="ratio",
        weight=0.19,
        source="Strukturierte Qualitätsberichte (G-BA/DeQS)",
    ),
    MetricDefinition(
        key="ppugv_quote",
        label="PpUGV-Konformität",
        description="Nursing staff minimum compliance rate (%).",
        unit="%",
        weight=0.24,
        source="PpUGV-Meldungen (InEK Pflege)",
    ),
    MetricDefinition(
        key="access_min",
        label="Erreichbarkeit",
        description="Average travel time in minutes to nearest Maximalversorger.",
        unit="min",
        weight=0.31,
        source="BKG / OSM routing (OSRM)",
    ),
    MetricDefinition(
        key="minq_quote",
        label="Mindestmengen-Konformität",
        description="Share of minimum volume requirements met (%).",
        unit="%",
        weight=0.14,
        source="Strukturierte Qualitätsberichte (G-BA/DeQS)",
    ),
    MetricDefinition(
        key="kap_auslast",
        label="Bettenauslastung",
        description="Bed occupancy rate (%).",
        unit="%",
        weight=0.12,
        source="§21-Daten (InEK / FDZ)",
    ),
]


@router.get("", response_model=list[MetricDefinition])
async def list_metrics() -> list[MetricDefinition]:
    """Return all metric definitions with labels, descriptions, units, and weights."""
    return METRICS
