"""Gold layer: compute Deficit Index and populate mart.einrichtung_kpi."""

from dagster import AssetExecutionContext, Output, StaticPartitionsDefinition, asset
from sqlalchemy import text

from pipeline.resources import DatabaseResource

BERICHTSJAHRE = StaticPartitionsDefinition(["2020", "2021", "2022", "2023"])

_KPI_FUSION_SQL = """
INSERT INTO mart.einrichtung_kpi (
    ik_nummer, berichtsjahr,
    quality_score, casemix_index,
    def_index, konfidenz, datenstand
)
SELECT
    e.ik_nummer,
    :berichtsjahr AS berichtsjahr,
    -- Quality deficit: fraction of Mindestmenge procedures NOT authorized (0=best, 1=worst)
    ROUND(1.0 - mm.minq_compliance, 4)            AS quality_score,
    -- No per-hospital DRG casemix available from current data sources
    NULL                                           AS casemix_index,
    -- Deficit Index 0–100 (higher = more supply deficit)
    ROUND((1.0 - mm.minq_compliance) * 100.0, 2) AS def_index,
    -- Confidence: 1.0 when MM data present (sole source)
    1.0                                            AS konfidenz,
    CURRENT_DATE                                   AS datenstand
FROM core.dim_einrichtung e
-- Mindestmenge compliance: fraction of MM procedures where hospital is authorized
JOIN (
    SELECT
        ik_nummer,
        ROUND(
            SUM(CASE WHEN (status->>'authorized')::boolean THEN 1 ELSE 0 END)::numeric
            / NULLIF(COUNT(*), 0)
        , 4) AS minq_compliance
    FROM core.fact_mindestmenge
    WHERE berichtsjahr = :berichtsjahr
    GROUP BY ik_nummer
) mm ON mm.ik_nummer = e.ik_nummer
WHERE e.is_current
ON CONFLICT (ik_nummer, berichtsjahr) DO UPDATE SET
    quality_score   = EXCLUDED.quality_score,
    casemix_index   = EXCLUDED.casemix_index,
    def_index       = EXCLUDED.def_index,
    konfidenz       = EXCLUDED.konfidenz,
    datenstand      = EXCLUDED.datenstand
"""


@asset(
    group_name="gold",
    partitions_def=BERICHTSJAHRE,
    deps=["dim_einrichtung", "mindestmengen"],
    description="Compute Deficit Index from Mindestmenge compliance into mart.einrichtung_kpi.",
)
def einrichtung_kpi(context: AssetExecutionContext, database: DatabaseResource) -> Output:
    """
    Gold layer fusion: compute the Deficit Index (0–100) from Mindestmenge compliance.

    - quality_score: fraction of MM procedures NOT authorized (0=fully compliant, 1=none met)
    - def_index: quality_score × 100 (higher = more supply deficit)
    - casemix_index: NULL (no per-hospital DRG source available)
    """
    berichtsjahr = int(context.partition_key)

    with database.get_sync_session() as session:
        result = session.execute(text(_KPI_FUSION_SQL), {"berichtsjahr": berichtsjahr})
        upserted = result.rowcount

    context.log.info(f"Upserted {upserted} KPI rows for {berichtsjahr}")
    return Output(value=upserted, metadata={"upserted_rows": upserted, "berichtsjahr": berichtsjahr})


@asset(
    group_name="gold",
    deps=["einrichtung_kpi"],
    description="Refresh mart.v_deficit_rank materialized view CONCURRENTLY.",
)
def deficit_rank(context: AssetExecutionContext, database: DatabaseResource) -> Output:
    """Refresh the pre-aggregated ranking view used by the /deficit/ranking API endpoint."""
    with database.get_sync_session() as session:
        row = session.execute(
            text("SELECT relispopulated FROM pg_class WHERE relname = 'v_deficit_rank' AND relkind = 'm'")
        ).fetchone()
        is_populated = row and row[0]

        if is_populated:
            session.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY mart.v_deficit_rank"))
        else:
            session.execute(text("REFRESH MATERIALIZED VIEW mart.v_deficit_rank"))

    context.log.info("Refreshed mart.v_deficit_rank")
    return Output(value=None, metadata={"refreshed": True})
