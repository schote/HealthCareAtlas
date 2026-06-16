from __future__ import annotations

from datetime import date

from sqlalchemy import Date, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class ConfigWeights(Base):
    """Versioned deficit engine weights — never hardcoded in SQL."""

    __tablename__ = "config_weights"
    __table_args__ = {"schema": "core"}

    version: Mapped[str] = mapped_column(Text, primary_key=True)
    metric_key: Mapped[str] = mapped_column(Text, primary_key=True)
    weight: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
