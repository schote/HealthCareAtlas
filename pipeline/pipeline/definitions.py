"""Dagster Definitions: register all assets, resources, schedules, and asset checks."""

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

all_assets = load_assets_from_package_module(assets_module)

bronze_job = define_asset_job(
    "bronze_ingestion",
    selection=AssetSelection.groups("bronze"),
    description="Ingest raw source files into the Bronze (raw) schema.",
)

silver_job = define_asset_job(
    "silver_transformation",
    selection=AssetSelection.groups("silver"),
    description="Transform Bronze data into typed, normalized Silver (core) tables.",
)

gold_job = define_asset_job(
    "gold_fusion",
    selection=AssetSelection.groups("gold"),
    description="Fuse Silver data and compute the Deficit Index into Gold (mart) tables.",
)

full_pipeline_job = define_asset_job(
    "full_pipeline",
    selection=AssetSelection.groups("bronze", "silver", "gold"),
    description="End-to-end pipeline: Bronze → Silver → Gold.",
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
    jobs=[bronze_job, silver_job, gold_job, full_pipeline_job],
    schedules=[annual_schedule],
    asset_checks=[kpi_freshness_check, kpi_range_check, kpi_confidence_check],
)
