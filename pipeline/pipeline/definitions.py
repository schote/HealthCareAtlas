"""Dagster Definitions: register all assets, resources, schedules, and asset checks."""

import os

from dagster import (
    AssetSelection,
    Definitions,
    EnvVar,
    ScheduleDefinition,
    define_asset_job,
    load_assets_from_package_module,
)

from pipeline import assets as assets_module
from pipeline.checks import kpi_confidence_check, kpi_freshness_check, kpi_range_check
from pipeline.resources import DatabaseResource

# Load all assets defined under pipeline/assets/
all_assets = load_assets_from_package_module(assets_module)

# Jobs
bronze_job = define_asset_job(
    "bronze_ingestion",
    selection=["qualitaetsberichte_raw", "drg_raw"],
    description="Ingest annual QB and DRG raw data into the Bronze schema.",
)

bronze_ppugv_job = define_asset_job(
    "bronze_ppugv_ingestion",
    selection=["ppugv_raw"],
    description="Ingest quarterly PpUGV nursing staff data into the Bronze schema.",
)

silver_job = define_asset_job(
    "silver_transformation",
    selection=["dim_einrichtung", "dim_region", "dim_zeit"],
    description="Transform Bronze data into Silver (core) normalized dimensions.",
)

gold_job = define_asset_job(
    "gold_fusion",
    selection=["einrichtung_kpi", "deficit_rank"],
    description="Fuse Silver data and compute Deficit Index into Gold (mart) layer.",
)

full_pipeline_job = define_asset_job(
    "full_pipeline",
    selection=AssetSelection.all() - AssetSelection.keys("ppugv_raw"),
    description="End-to-end annual pipeline: Bronze → Silver → Gold (ppugv_raw runs separately via bronze_ppugv_ingestion).",
)

# Annual schedule: run full pipeline on 1st of February each year (after annual data release)
annual_schedule = ScheduleDefinition(
    name="annual_pipeline_schedule",
    job=full_pipeline_job,
    cron_schedule="0 6 1 2 *",  # 06:00 UTC on Feb 1st
    description="Annual full pipeline run triggered after Qualitätsbericht data release.",
)

defs = Definitions(
    assets=all_assets,
    resources={
        "database": DatabaseResource(
            database_url=EnvVar("DATABASE_URL"),
            database_url_sync=EnvVar("DATABASE_URL_SYNC"),
        ),
    },
    jobs=[bronze_job, bronze_ppugv_job, silver_job, gold_job, full_pipeline_job],
    schedules=[annual_schedule],
    asset_checks=[kpi_freshness_check, kpi_range_check, kpi_confidence_check],
)
