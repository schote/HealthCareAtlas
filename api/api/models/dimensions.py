from __future__ import annotations

import enum
from datetime import date

from sqlalchemy import CHAR, Boolean, Date, Enum, Integer, Numeric, SmallInteger, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class VersorgungsstufeEnum(str, enum.Enum):
    Grund = "Grund"
    Regel = "Regel"
    Schwerpunkt = "Schwerpunkt"
    Maximal = "Maximal"


class TraegerschaftEnum(str, enum.Enum):
    oeffentlich = "oeffentlich"
    freigemeinnuetzig = "freigemeinnuetzig"
    privat = "privat"


class DimRegion(Base):
    __tablename__ = "dim_region"
    __table_args__ = {"schema": "core"}

    ags: Mapped[str] = mapped_column(CHAR(8), primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    ebene: Mapped[str] = mapped_column(Text, nullable=False)
    parent_ags: Mapped[str | None] = mapped_column(CHAR(8))
    einwohner: Mapped[int | None] = mapped_column(Integer)
    anteil_65plus: Mapped[float | None] = mapped_column(Numeric(5, 2))
    morbiditaet_idx: Mapped[float | None] = mapped_column(Numeric(6, 3))


class DimEinrichtung(Base):
    __tablename__ = "dim_einrichtung"
    __table_args__ = {"schema": "core"}

    sk: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ik_nummer: Mapped[str] = mapped_column(CHAR(9), nullable=False, index=True)
    standort_id: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str | None] = mapped_column(Text)
    ags: Mapped[str | None] = mapped_column(CHAR(8))
    versorgungsstufe: Mapped[VersorgungsstufeEnum | None] = mapped_column(
        Enum(VersorgungsstufeEnum, schema="core", name="versorgungsstufe_enum")
    )
    traegerschaft: Mapped[TraegerschaftEnum | None] = mapped_column(
        Enum(TraegerschaftEnum, schema="core", name="traegerschaft_enum")
    )
    plz: Mapped[str | None] = mapped_column(CHAR(5))
    ort: Mapped[str | None] = mapped_column(Text)
    strasse: Mapped[str | None] = mapped_column(Text)
    betten: Mapped[int | None] = mapped_column(Integer)
    lat: Mapped[float | None] = mapped_column(Numeric(9, 6))
    lon: Mapped[float | None] = mapped_column(Numeric(9, 6))
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_to: Mapped[date] = mapped_column(Date, nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class DimZeit(Base):
    __tablename__ = "dim_zeit"
    __table_args__ = {"schema": "core"}

    berichtsjahr: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    quartal: Mapped[int] = mapped_column(SmallInteger, primary_key=True)


class DimFachabteilung(Base):
    __tablename__ = "dim_fachabteilung"
    __table_args__ = {"schema": "core"}

    fab_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bezeichnung: Mapped[str] = mapped_column(Text, nullable=False)
    ldkr_code: Mapped[str | None] = mapped_column(Text)


class DimQualitaetsindikator(Base):
    """Catalog of G-BA quality indicator definitions."""

    __tablename__ = "dim_qualitaetsindikator"
    __table_args__ = {"schema": "core"}

    kennzahl_id: Mapped[str] = mapped_column(Text, primary_key=True)
    bezeichnung: Mapped[str | None] = mapped_column(Text)
    leistungsbereich: Mapped[str | None] = mapped_column(Text)
    rechenregel: Mapped[str | None] = mapped_column(Text)
    datenquelle: Mapped[str | None] = mapped_column(Text)  # "QB" | "DeQS"
    ist_planungsrelevant: Mapped[bool | None] = mapped_column(Boolean)
