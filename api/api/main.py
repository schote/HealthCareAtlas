"""Versorgungsatlas FastAPI application entry point."""

import json
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import (
    deficit_router,
    hospitals_router,
    hospitals_indicators_router,
    indicators_router,
    metrics_router,
    regions_router,
)

CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "http://localhost,http://localhost:80").split(",")
OPENAPI_OUTPUT = Path("/app/packages/contracts/openapi.json")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Export OpenAPI spec on startup for TypeScript codegen
    yield
    spec = app.openapi()
    try:
        OPENAPI_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OPENAPI_OUTPUT.write_text(json.dumps(spec, indent=2))
    except OSError:
        pass  # Non-critical in environments without the contracts volume


app = FastAPI(
    title="Versorgungsatlas API",
    description=(
        "REST API for the German Healthcare Supply Atlas (Versorgungsatlas). "
        "Provides hospital KPIs, regional data, and the Deficit Index derived from "
        "Qualitätsberichte, §21 DRG data, PpUGV nursing data, and geo/routing data."
    ),
    version="0.1.0",
    contact={"name": "Versorgungsatlas Team"},
    license_info={"name": "DL-DE-BY 2.0"},
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(hospitals_router)
app.include_router(hospitals_indicators_router)
app.include_router(regions_router)
app.include_router(metrics_router)
app.include_router(deficit_router)
app.include_router(indicators_router)


@app.get("/health", tags=["system"])
async def health() -> dict:
    return {"status": "ok", "service": "versorgungsatlas-api"}
