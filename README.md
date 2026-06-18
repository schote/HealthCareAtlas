# HealthCareAtlas

German Healthcare Supply Atlas — a data pipeline and web application for computing and visualising hospital deficit indices from Strukturierte Qualitätsberichte (QB) and §21 DRG case data.

## Architecture

```
data/raw/          Raw source files (QB XML, DRG CSV)
pipeline/          Dagster pipeline  →  bronze / silver / gold layers
alembic/           Database schema migrations
api/               FastAPI REST API
web/               React frontend
```

| Service       | URL                       |
|---------------|---------------------------|
| Frontend      | http://localhost:8081      |
| API           | http://localhost:8001      |
| Dagster UI    | http://localhost:3001      |
| PostgreSQL    | localhost:5433             |

## Prerequisites

- Docker and Docker Compose
- Raw data files placed under `data/raw/` (see layout below)

```
data/raw/
  qb/
    2022/   ← Strukturierte Qualitätsberichte XML files
    2023/
  drg/
    2022/   ← §21 DRG case data CSV files (semicolon-delimited)
    2023/
```

## Setup

**1. Start all services**

```bash
docker compose up -d
```

**2. Run database migrations** (once after first start, and after any schema update)

```bash
docker compose run --rm migrate
```

**3. Materialize the data pipeline**

Open the Dagster UI at http://localhost:3001, navigate to **Assets**, select all assets for partition `2022`, and click **Materialize selected**.

Run in this order (Dagster respects dependencies automatically if you select all):

| Step   | Asset                   | What it does                                      |
|--------|-------------------------|---------------------------------------------------|
| Bronze | `qualitaetsberichte_raw`| Ingest QB XML files → `raw.qualitaetsbericht`    |
| Bronze | `drg_raw`               | Ingest DRG CSVs → `raw.drg_fallzahlen`           |
| Silver | `qualitaetsindikatoren` | Parse QB → `core.fact_qualitaetsindikator`        |
| Silver | `fact_drg`              | Cast DRG → `core.fact_drg`                       |
| Gold   | `einrichtung_kpi`       | Compute Deficit Index → `mart.einrichtung_kpi`   |

**4. Open the app**

http://localhost:8081

## Updating after code changes

**API or pipeline code change** — rebuild the affected service:

```bash
docker compose up -d --build api
docker compose up -d --build dagster-webserver dagster-daemon
```

**Schema change** — add a migration file under `alembic/versions/`, then:

```bash
docker compose run --rm migrate
```

## Deficit Index

The composite index (0–100, higher = more deficit) is computed per hospital per reporting year from two sources:

- **Quality score** (70 %): fraction of QB quality indicators flagged *auffaellig*
- **Casemix index** (30 %): average DRG CMI — lower specialisation = higher deficit

Weights are stored in `core.config_weights` and can be updated without code changes.
