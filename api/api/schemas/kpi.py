from datetime import date

from pydantic import BaseModel, Field


class MetricDefinition(BaseModel):
    key: str
    label: str
    description: str
    unit: str
    weight: float = Field(ge=0, le=1)
    source: str


class KPI(BaseModel):
    ik_nummer: str
    berichtsjahr: int
    def_index: float = Field(ge=0, le=100)
    quality_score: float | None = None
    casemix_index: float | None = None
    konfidenz: float = Field(ge=0, le=1)
    datenstand: date

    model_config = {"from_attributes": True}


class DeficitRankingItem(BaseModel):
    rang: int
    entity_id: str
    name: str | None
    ebene: str
    metric_key: str
    score: float
    berichtsjahr: int


class DeficitRanking(BaseModel):
    total: int
    berichtsjahr: int
    items: list[DeficitRankingItem]
