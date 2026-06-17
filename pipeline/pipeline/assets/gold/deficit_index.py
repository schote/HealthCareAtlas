"""Gold layer: compute Deficit Index and populate mart.einrichtung_kpi."""

from dagster import AssetExecutionContext, Output, StaticPartitionsDefinition, asset
from sqlalchemy import text

from pipeline.resources import DatabaseResource

BERICHTSJAHRE = StaticPartitionsDefinition(["2020", "2021", "2022", "2023"])

_KPI_FUSION_SQL = """
INSERT INTO mart.einrichtung_kpi (
    ik_nummer, berichtsjahr,
    mort_adj, ppugv_quote, access_min, minq_quote, casemix_index, betten,
    def_index, konfidenz, datenstand
)
SELECT
    e.ik_nummer,
    :berichtsjahr AS berichtsjahr,
    -- Risk-adjusted mortality (from fact_qualitaet)
    COALESCE(q.smr_adj, 1.0)                         AS mort_adj,
    -- PpUGV nursing compliance (avg over quarters)
    COALESCE(p.schichten_konform_avg, 100.0)          AS ppugv_quote,
    -- Average travel time in minutes (from fact_erreichbarkeit)
    COALESCE(er.fahrzeit_maxvers, 30.0)               AS access_min,
    -- Minimum volume compliance rate
    COALESCE(mq.minq_quote, 100.0)                    AS minq_quote,
    -- Casemix index from DRG data
    COALESCE(d.casemix_index, 1.0)                    AS casemix_index,
    -- Bed count from capacity facts
    COALESCE(k.betten, 0)                             AS betten,
    -- Deficit Index: weighted composite (weights from config_weights)
    ROUND(
        (
            -- Mortality component (weight ~19%)
            (LEAST(COALESCE(q.smr_adj, 1.0) / 2.0, 1.0)) * w.w_mort
            -- PpUGV staffing deficit (weight ~24%): lower compliance = higher deficit
            + ((100.0 - COALESCE(p.schichten_konform_avg, 100.0)) / 100.0) * w.w_ppugv
            -- Access time component (weight ~31%): normalize to 0–1 over 60 min max
            + (LEAST(COALESCE(er.fahrzeit_maxvers, 30.0) / 60.0, 1.0)) * w.w_access
            -- Minimum volume deficit (weight ~14%)
            + ((100.0 - COALESCE(mq.minq_quote, 100.0)) / 100.0) * w.w_minq
            -- Capacity / occupancy (weight ~12%)
            + (LEAST(COALESCE(k.bettenauslastung, 80.0) / 100.0, 1.0)) * w.w_kap
        ) * 100.0
    , 2)                                              AS def_index,
    -- Data quality confidence: fraction of non-null KPI sources
    ROUND(
        (
            (CASE WHEN q.smr_adj IS NOT NULL THEN 1 ELSE 0 END)
          + (CASE WHEN p.schichten_konform_avg IS NOT NULL THEN 1 ELSE 0 END)
          + (CASE WHEN er.fahrzeit_maxvers IS NOT NULL THEN 1 ELSE 0 END)
          + (CASE WHEN mq.minq_quote IS NOT NULL THEN 1 ELSE 0 END)
          + (CASE WHEN k.betten IS NOT NULL THEN 1 ELSE 0 END)
        )::numeric / 5.0
    , 2)                                              AS konfidenz,
    CURRENT_DATE                                      AS datenstand
FROM core.dim_einrichtung e
-- Weights from versioned config
CROSS JOIN (
    SELECT
        MAX(weight) FILTER (WHERE metric_key = 'mort_adj')    AS w_mort,
        MAX(weight) FILTER (WHERE metric_key = 'ppugv_quote') AS w_ppugv,
        MAX(weight) FILTER (WHERE metric_key = 'access_min')  AS w_access,
        MAX(weight) FILTER (WHERE metric_key = 'minq_quote')  AS w_minq,
        MAX(weight) FILTER (WHERE metric_key = 'kap_auslast') AS w_kap
    FROM core.config_weights
    WHERE valid_from = (SELECT MAX(valid_from) FROM core.config_weights)
) w
-- Quality facts
LEFT JOIN (
    SELECT ik_nummer, AVG(smr_adj) AS smr_adj
    FROM core.fact_qualitaet
    WHERE berichtsjahr = :berichtsjahr
    GROUP BY ik_nummer
) q ON q.ik_nummer = e.ik_nummer
-- PpUGV facts (average over quarters)
LEFT JOIN (
    SELECT ik_nummer, AVG(schichten_konform) AS schichten_konform_avg
    FROM core.fact_ppugv
    WHERE berichtsjahr = :berichtsjahr
    GROUP BY ik_nummer
) p ON p.ik_nummer = e.ik_nummer
-- Accessibility facts
LEFT JOIN (
    SELECT fe.ik_nummer, AVG(er.fahrzeit_maxvers) AS fahrzeit_maxvers
    FROM core.fact_erreichbarkeit er
    JOIN core.dim_einrichtung fe ON fe.standort_id = er.standort_id AND fe.is_current
    GROUP BY fe.ik_nummer
) er ON er.ik_nummer = e.ik_nummer
-- Minimum volume compliance
LEFT JOIN (
    SELECT
        ik_nummer,
        ROUND(
            100.0 * SUM(CASE WHEN (status->>'konform')::boolean THEN 1 ELSE 0 END)
            / NULLIF(COUNT(*), 0)
        , 1) AS minq_quote
    FROM core.fact_mindestmenge
    WHERE berichtsjahr = :berichtsjahr
    GROUP BY ik_nummer
) mq ON mq.ik_nummer = e.ik_nummer
-- DRG casemix index (avg over DRG codes per hospital)
LEFT JOIN (
    SELECT ik_nummer, AVG(casemix_index) AS casemix_index
    FROM core.fact_drg
    WHERE berichtsjahr = :berichtsjahr
    GROUP BY ik_nummer
) d ON d.ik_nummer = e.ik_nummer
-- Capacity facts
LEFT JOIN (
    SELECT ik_nummer, betten, bettenauslastung
    FROM core.fact_kapazitaet
    WHERE berichtsjahr = :berichtsjahr
) k ON k.ik_nummer = e.ik_nummer
WHERE e.is_current
ON CONFLICT (ik_nummer, berichtsjahr) DO UPDATE SET
    mort_adj        = EXCLUDED.mort_adj,
    ppugv_quote     = EXCLUDED.ppugv_quote,
    access_min      = EXCLUDED.access_min,
    minq_quote      = EXCLUDED.minq_quote,
    casemix_index   = EXCLUDED.casemix_index,
    betten          = EXCLUDED.betten,
    def_index       = EXCLUDED.def_index,
    konfidenz       = EXCLUDED.konfidenz,
    datenstand      = EXCLUDED.datenstand
"""


@asset(
    group_name="gold",
    partitions_def=BERICHTSJAHRE,
    deps=["dim_einrichtung", "dim_region"],
    description="Fuse all KPI fact tables into mart.einrichtung_kpi and compute Deficit Index.",
)
def einrichtung_kpi(context: AssetExecutionContext, database: DatabaseResource) -> Output:
    """
    Gold layer fusion: join quality, staffing, accessibility, capacity and
    minimum-volume facts to compute the composite Deficit Index (0–100)
    for each hospital per Berichtsjahr.

    Weights are read from core.config_weights (versioned) so they can be
    adjusted without code changes.
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
        session.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY mart.v_deficit_rank"))

    context.log.info("Refreshed mart.v_deficit_rank")
    return Output(value=None, metadata={"refreshed": True})
