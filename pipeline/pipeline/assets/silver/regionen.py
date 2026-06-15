"""Silver layer: populate core.dim_region from BKG geodata and Destatis demographics."""

import pandas as pd
from dagster import AssetExecutionContext, Output, asset

from pipeline.resources import DatabaseResource

_UPSERT_SQL = """
INSERT INTO core.dim_region (ags, name, ebene, parent_ags, einwohner, anteil_65plus, morbiditaet_idx)
SELECT ags, name, ebene, parent_ags, einwohner, anteil_65plus, morbiditaet_idx
FROM staging_region
ON CONFLICT (ags) DO UPDATE SET
    name             = EXCLUDED.name,
    einwohner        = EXCLUDED.einwohner,
    anteil_65plus    = EXCLUDED.anteil_65plus,
    morbiditaet_idx  = EXCLUDED.morbiditaet_idx
"""


@asset(
    group_name="silver",
    description="Load BKG municipality boundaries + Destatis demographics into core.dim_region.",
    required_resource_keys={"database"},
)
def dim_region(context: AssetExecutionContext, database: DatabaseResource) -> Output:
    """
    Build core.dim_region from:
    - BKG GeoJSON (Amtliche Gemeindeschlüssel + geometry)
    - Destatis GENESIS-API (population, age distribution)
    - RKI morbidity index

    Hierarchical structure: Gemeinde → Kreis → Land → Bund (via parent_ags).
    """
    # TODO: fetch from GENESIS-API (https://www-genesis.destatis.de/datenbank/online/statistic/12411)
    # and BKG open data GeoJSON
    context.log.info("dim_region: TODO implement GENESIS-API and BKG GeoJSON ingestion")
    return Output(value=0, metadata={"upserted_rows": 0})
