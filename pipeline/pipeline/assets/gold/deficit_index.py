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
    -- QB quality deficit: fraction of indicators flagged auffaellig (0–1, higher = worse)
    COALESCE(q.quality_score, 0.5)                        AS quality_score,
    -- DRG casemix index: avg over all DRG codes for this hospital/year
    COALESCE(d.casemix_index, 1.0)                        AS casemix_index,
    -- Deficit Index: weighted composite (weights from core.config_weights)
    ROUND(
        (
            -- Quality component: direct fraction (0–1)
            COALESCE(q.quality_score, 0.5) * w.w_quality
            -- Casemix component: lower CMI = less specialized = higher supply deficit
            + (1.0 - LEAST(COALESCE(d.casemix_index, 1.0) / 2.0, 1.0)) * w.w_casemix
        ) * 100.0
    , 2)                                                  AS def_index,
    -- Confidence: fraction of sources with real (non-default) data
    ROUND(
        (
            (CASE WHEN q.quality_score IS NOT NULL THEN 1 ELSE 0 END)
          + (CASE WHEN d.casemix_index IS NOT NULL THEN 1 ELSE 0 END)
        )::numeric / 2.0
    , 2)                                                  AS konfidenz,
    CURRENT_DATE                                          AS datenstand
FROM core.dim_einrichtung e
-- Weights from versioned config
CROSS JOIN (
    SELECT
        MAX(weight) FILTER (WHERE metric_key = 'quality')  AS w_quality,
        MAX(weight) FILTER (WHERE metric_key = 'casemix')  AS w_casemix
    FROM core.config_weights
    WHERE valid_from = (SELECT MAX(valid_from) FROM core.config_weights)
) w
-- Quality deficit from QB indicators: fraction flagged auffaellig
LEFT JOIN (
    SELECT
        ik_nummer,
        ROUND(
            SUM(CASE WHEN auffaellig THEN 1 ELSE 0 END)::numeric / NULLIF(COUNT(*), 0)
        , 2) AS quality_score
    FROM core.fact_qualitaetsindikator
    WHERE berichtsjahr = :berichtsjahr
    GROUP BY ik_nummer
) q ON q.ik_nummer = e.ik_nummer
-- Casemix index from DRG data
LEFT JOIN (
    SELECT ik_nummer, ROUND(AVG(casemix_index), 3) AS casemix_index
    FROM core.fact_drg
    WHERE berichtsjahr = :berichtsjahr
    GROUP BY ik_nummer
) d ON d.ik_nummer = e.ik_nummer
WHERE e.is_current
  AND (q.quality_score IS NOT NULL OR d.casemix_index IS NOT NULL)
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
    deps=["dim_einrichtung", "qualitaetsindikatoren", "fact_drg"],
    description="Fuse QB quality and DRG casemix facts into mart.einrichtung_kpi and compute Deficit Index.",
)
def einrichtung_kpi(context: AssetExecutionContext, database: DatabaseResource) -> Output:
    """
    Gold layer fusion: join QB quality indicators and DRG casemix facts to compute
    the composite Deficit Index (0–100) for each hospital per Berichtsjahr.

    - quality_score: fraction of QB indicators flagged auffaellig (higher = worse quality)
    - casemix_index: avg DRG CMI (lower = less specialized = higher supply deficit)

    Weights are read from core.config_weights (versioned, metric_keys: quality / casemix).
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
