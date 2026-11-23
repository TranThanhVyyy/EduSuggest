from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class RecommendedCourse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    maKhoaHoc: int
    tieuDe: str | None
    moTa: str | None
    maDanhMuc: int | None
    trinhDo: str | None
    thoiLuong: int | None
    gia: Decimal | None
    score: float | None = Field(ge=0, le=1)
    reasonCodes: list[str]


class CourseRecommendationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[RecommendedCourse]
    strategy: Literal["content_based", "latest", "none"]
    personalized: bool


class RecommendedMaterial(BaseModel):
    model_config = ConfigDict(extra="forbid")

    maTaiLieu: int
    maBaiHoc: int
    maKhoaHoc: int
    tieuDe: str | None
    moTa: str | None
    loai: str | None
    score: float = Field(ge=0, le=1)
    reasonCodes: list[str]


class MaterialRecommendationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[RecommendedMaterial]
