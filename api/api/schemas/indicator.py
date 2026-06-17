from pydantic import BaseModel


class QualitaetsindikatorResult(BaseModel):
    kennzahl_id: str
    leistungsbereich: str | None
    bezeichnung: str | None
    zaehler: int | None
    nenner: int | None
    ergebnis: float | None
    referenzbereich_von: float | None
    referenzbereich_bis: float | None
    auffaellig: bool | None
    ist_planungsrelevant: bool | None

    model_config = {"from_attributes": True}


class QualitaetsindikatorGroup(BaseModel):
    leistungsbereich: str
    indicators: list[QualitaetsindikatorResult]
    auffaellig_count: int
    total_count: int


class HospitalIndicators(BaseModel):
    ik_nummer: str
    berichtsjahr: int
    groups: list[QualitaetsindikatorGroup]
    total_indicators: int
    total_auffaellig: int


class QualitaetsindikatorKatalog(BaseModel):
    kennzahl_id: str
    bezeichnung: str | None
    leistungsbereich: str | None
    rechenregel: str | None
    datenquelle: str | None
    ist_planungsrelevant: bool | None

    model_config = {"from_attributes": True}
