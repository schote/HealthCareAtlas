"""SQLAlchemy ORM models for the Versorgungsatlas API.

Importing this package registers all models with Base.metadata, which
enables Alembic autogenerate (alembic revision --autogenerate) to detect
schema drift between ORM definitions and the live database.
"""

from .base import Base
from .config import ConfigWeights
from .dimensions import (
    DimEinrichtung,
    DimFachabteilung,
    DimQualitaetsindikator,
    DimRegion,
    DimZeit,
    TraegerschaftEnum,
    VersorgungsstufeEnum,
)
from .facts import (
    FactDrg,
    FactErreichbarkeit,
    FactKapazitaet,
    FactMindestmenge,
    FactPpugv,
    FactQualitaet,
    FactQualitaetsindikator,
)
from .mart import EinrichtungKpi

__all__ = [
    "Base",
    "ConfigWeights",
    "DimEinrichtung",
    "DimFachabteilung",
    "DimQualitaetsindikator",
    "DimRegion",
    "DimZeit",
    "TraegerschaftEnum",
    "VersorgungsstufeEnum",
    "FactDrg",
    "FactErreichbarkeit",
    "FactKapazitaet",
    "FactMindestmenge",
    "FactPpugv",
    "FactQualitaet",
    "FactQualitaetsindikator",
    "EinrichtungKpi",
]
