from pydantic import BaseModel


class Region(BaseModel):
    ags: str
    name: str
    ebene: str
    parent_ags: str | None = None
    einwohner: int | None = None
    anteil_65plus: float | None = None
    morbiditaet_idx: float | None = None

    model_config = {"from_attributes": True}


class RegionDetail(Region):
    children: list["Region"] = []
