from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


class HospitalKPI(BaseModel):
    berichtsjahr: int
    def_index: float = Field(ge=0, le=100, description="Deficit Index 0–100")
    mort_adj: float | None = Field(None, description="Risk-adjusted SMR")
    ppugv_quote: float | None = Field(None, description="Nursing staff compliance %")
    access_min: float | None = Field(None, description="Travel time to nearest Maximalversorger (min)")
    minq_quote: float | None = Field(None, description="Minimum volume compliance %")
    casemix_index: float | None = None
    betten: int | None = None
    konfidenz: float = Field(ge=0, le=1, description="Data quality confidence score")
    datenstand: date


class Hospital(BaseModel):
    ik_nummer: str
    name: str | None
    ort: str | None
    plz: str | None
    ags: str | None
    versorgungsstufe: Literal["Grund", "Regel", "Schwerpunkt", "Maximal"] | None
    kpi: HospitalKPI | None = None

    model_config = {"from_attributes": True}


class HospitalDetail(Hospital):
    strasse: str | None = None
    standort_id: str | None = None


class HospitalList(BaseModel):
    total: int
    items: list[Hospital]
    page: int
    page_size: int
