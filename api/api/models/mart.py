from __future__ import annotations

from datetime import date

from sqlalchemy import CHAR, Date, Integer, Numeric, SmallInteger
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class EinrichtungKpi(Base):
    """Gold mart: fused KPI row per hospital per Berichtsjahr."""

    __tablename__ = "einrichtung_kpi"
    __table_args__ = {"schema": "mart"}

    ik_nummer: Mapped[str] = mapped_column(CHAR(9), primary_key=True)
    berichtsjahr: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    mort_adj: Mapped[float | None] = mapped_column(Numeric(4, 2))
    ppugv_quote: Mapped[float | None] = mapped_column(Numeric(5, 2))
    access_min: Mapped[float | None] = mapped_column(Numeric(6, 2))
    minq_quote: Mapped[float | None] = mapped_column(Numeric(5, 2))
    casemix_index: Mapped[float | None] = mapped_column(Numeric(5, 3))
    betten: Mapped[int | None] = mapped_column(Integer)
    def_index: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    konfidenz: Mapped[float] = mapped_column(Numeric(3, 2), nullable=False)
    datenstand: Mapped[date] = mapped_column(Date, nullable=False)
