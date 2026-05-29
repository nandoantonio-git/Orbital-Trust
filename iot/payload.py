from datetime import datetime, timezone
from typing import Any, Dict


_REQUIRED_FIELDS = (
    "event_id",
    "timestamp",
    "area_id",
    "source",
    "detected_class",
    "class_percentage",
    "change_score",
    "cloud_score",
    "shadow_score",
    "image_quality",
    "cv_confidence",
    "frame_reference",
)


def build_payload(
    event_id: str,
    area_id: str,
    source: str,
    detector_result: Dict[str, Any],
    quality_result: Dict[str, Any],
    change_score: float,
    frame_reference: str,
) -> dict:
    payload = {
        "event_id": event_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "area_id": area_id,
        "source": source,
        "detected_class": detector_result["detected_class"],
        "class_percentage": detector_result["class_percentage"],
        "change_score": change_score,
        "cloud_score": quality_result["cloud_score"],
        "shadow_score": quality_result["shadow_score"],
        "image_quality": quality_result["image_quality"],
        "cv_confidence": quality_result["cv_confidence"],
        "frame_reference": frame_reference,
    }

    missing = [f for f in _REQUIRED_FIELDS if payload.get(f) is None]
    if missing:
        raise ValueError(f"Campos obrigatórios ausentes: {missing}")

    return payload
