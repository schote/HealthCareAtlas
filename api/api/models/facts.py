from __future__ import annotations

from sqlalchemy import CHAR, Boolean, Integer, Numeric, SmallInteger, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class FactQualitaet(Base):
    """Quality report summary facts (SMR, complication rate, hygiene score)."""

    __tablename__ = "fact_qualitaet"
    __table_args__ = {
        "schema": "core",
        "postgresql_partition_by": "RANGE (berichtsjahr)",
    }

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ik_nummer: Mapped[str] = mapped_column(CHAR(9), nullable=False)
    berichtsjahr: Mapped[int] = mapped_column(SmallInteger, nullable=False, primary_key=True)
    fab_id: Mapped[int | None] = mapped_column(Integer)
    smr: Mapped[float | None] = mapped_column(Numeric(4, 2))
    smr_adj: Mapped[float | None] = mapped_column(Numeric(4, 2))
    komplikationsrate: Mapped[float | None] = mapped_column(Numeric(5, 3))
    hygiene_score: Mapped[int | None] = mapped_column(SmallInteger)


class FactQualitaetsindikator(Base):
    """
    Per-indicator quality results extracted from Qualitätsberichte (QB/DeQS).

    One row per hospital × berichtsjahr × kennzahl_id.  Numerator (zaehler),
    denominator (nenner), result (ergebnis) and threshold breach flag are
    stored so the Deficit Engine can weight individual indicator families.
    """

    __tablename__ = "fact_qualitaetsindikator"
    __table_args__ = {
        "schema": "core",
        "postgresql_partition_by": "RANGE (berichtsjahr)",
    }

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ik_nummer: Mapped[str] = mapped_column(CHAR(9), nullable=False)
    berichtsjahr: Mapped[int] = mapped_column(SmallInteger, nullable=False, primary_key=True)
    kennzahl_id: Mapped[str] = mapped_column(Text, nullable=False)
    leistungsbereich: Mapped[str | None] = mapped_column(Text)
    bezeichnung: Mapped[str | None] = mapped_column(Text)
    zaehler: Mapped[int | None] = mapped_column(Integer)
    nenner: Mapped[int | None] = mapped_column(Integer)
    ergebnis: Mapped[float | None] = mapped_column(Numeric(10, 4))
    referenzbereich_von: Mapped[float | None] = mapped_column(Numeric(10, 4))
    referenzbereich_bis: Mapped[float | None] = mapped_column(Numeric(10, 4))
    auffaellig: Mapped[bool | None] = mapped_column(Boolean)
    ist_planungsrelevant: Mapped[bool | None] = mapped_column(Boolean)


class FactDrg(Base):
    __tablename__ = "fact_drg"
    __table_args__ = {
        "schema": "core",
        "postgresql_partition_by": "RANGE (berichtsjahr)",
    }

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ik_nummer: Mapped[str] = mapped_column(CHAR(9), nullable=False)
    berichtsjahr: Mapped[int] = mapped_column(SmallInteger, nullable=False, primary_key=True)
    drg_code: Mapped[str] = mapped_column(Text, nullable=False)
    fallzahl: Mapped[int | None] = mapped_column(Integer)
    verweildauer: Mapped[float | None] = mapped_column(Numeric(5, 2))
    casemix_index: Mapped[float | None] = mapped_column(Numeric(5, 3))


class FactKapazitaet(Base):
    __tablename__ = "fact_kapazitaet"
    __table_args__ = {
        "schema": "core",
        "postgresql_partition_by": "RANGE (berichtsjahr)",
    }

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ik_nummer: Mapped[str] = mapped_column(CHAR(9), nullable=False)
    berichtsjahr: Mapped[int] = mapped_column(SmallInteger, nullable=False, primary_key=True)
    betten: Mapped[int | None] = mapped_column(Integer)
    bettenauslastung: Mapped[float | None] = mapped_column(Numeric(5, 2))


class FactPpugv(Base):
    __tablename__ = "fact_ppugv"
    __table_args__ = {
        "schema": "core",
        "postgresql_partition_by": "RANGE (berichtsjahr)",
    }

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ik_nummer: Mapped[str] = mapped_column(CHAR(9), nullable=False)
    berichtsjahr: Mapped[int] = mapped_column(SmallInteger, nullable=False, primary_key=True)
    quartal: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    bereich: Mapped[str] = mapped_column(Text, nullable=False)
    schichten_konform: Mapped[float | None] = mapped_column(Numeric(5, 2))
    patient_pflege: Mapped[float | None] = mapped_column(Numeric(5, 2))
    untergrenze: Mapped[float | None] = mapped_column(Numeric(5, 2))


class FactMindestmenge(Base):
    __tablename__ = "fact_mindestmenge"
    __table_args__ = {
        "schema": "core",
        "postgresql_partition_by": "RANGE (berichtsjahr)",
    }

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ik_nummer: Mapped[str] = mapped_column(CHAR(9), nullable=False)
    berichtsjahr: Mapped[int] = mapped_column(SmallInteger, nullable=False, primary_key=True)
    ops_code: Mapped[str] = mapped_column(Text, nullable=False)
    soll: Mapped[int | None] = mapped_column(Integer)
    ist: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[dict | None] = mapped_column(JSONB)


class FactErreichbarkeit(Base):
    __tablename__ = "fact_erreichbarkeit"
    __table_args__ = {"schema": "core"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    standort_id: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    ags: Mapped[str | None] = mapped_column(CHAR(8))
    fahrzeit_maxvers: Mapped[float | None] = mapped_column(Numeric(6, 2))
    einwohner_einzug: Mapped[int | None] = mapped_column(Integer)
