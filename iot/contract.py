from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


RiskLevel = Literal["baixo", "medio", "alto"]
DetectedClass = Literal[
    "vegetacao",
    "solo_exposto",
    "agua",
    "queimada",
    "baixa_visibilidade",
]
ContractSource = Literal["Sentinel-2", "Landsat", "FIRMS", "INPE"]
ImageQuality = Literal["boa", "media", "baixa"]

CV_ALGORITHM_VERSION = "orbital-cv-v0.2.0"

IOT_PAYLOAD_REQUIRED_FIELDS = (
    "event_id",
    "timestamp",
    "area_id",
    "source",
    "detected_class",
    "class_percentage",
    "change_score",
    "cloud_score",
    "shadow_score",
    "brightness_score",
    "blur_score",
    "image_quality",
    "cv_confidence",
    "frame_reference",
    "algorithm_version",
)


class IoTPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    event_id: str = Field(min_length=1)
    timestamp: str = Field(min_length=1)
    area_id: str = Field(min_length=1)
    source: ContractSource
    detected_class: DetectedClass
    class_percentage: float = Field(ge=0.0, le=100.0)
    change_score: float = Field(ge=0.0, le=1.0)
    cloud_score: float = Field(ge=0.0, le=1.0)
    shadow_score: float = Field(ge=0.0, le=1.0)
    brightness_score: float = Field(ge=0.0, le=1.0)
    blur_score: float = Field(ge=0.0, le=1.0)
    image_quality: ImageQuality
    cv_confidence: float = Field(ge=0.0, le=1.0)
    frame_reference: str = Field(min_length=1)
    algorithm_version: str = Field(min_length=1)

    @field_validator("event_id", "timestamp", "area_id", "frame_reference", "algorithm_version")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("campo obrigatório não pode ser vazio")
        return value

    @field_validator("timestamp")
    @classmethod
    def _timestamp_is_iso8601(cls, value: str) -> str:
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("timestamp deve usar formato ISO 8601") from exc
        return value
