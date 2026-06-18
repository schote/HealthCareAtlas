from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


class HospitalKPI(BaseModel):
    berichtsjahr: int
    def_index: float = Field(ge=0, le=100, description="Deficit Index 0-100")
    quality_score: float | None = Field(None, description="Fraction of QB indicators flagged auffaellig (0-1)")
    casemix_index: float | None = Field(None, description="Average DRG casemix index")
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
