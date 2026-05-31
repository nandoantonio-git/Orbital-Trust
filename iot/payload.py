"""Build the required IoT -> ML/API payload contract.

`tile_quality` is internal pipeline metadata used for tile audit/fallback. It is
not a required contract field and is appended outside `build_payload` only when a
pipeline caller needs that diagnostic detail.
"""

from datetime import datetime, timezone
from typing import Any, Dict

from iot.contract import CV_ALGORITHM_VERSION, IOT_PAYLOAD_REQUIRED_FIELDS, IoTPayload


_REQUIRED_FIELDS = IOT_PAYLOAD_REQUIRED_FIELDS

OPTIONAL_INTERNAL_METADATA_FIELDS = ("tile_quality",)


def build_payload(
    event_id: str,
    area_id: str,
    source: str,
    detector_result: Dict[str, Any],
    quality_result: Dict[str, Any],
    change_score: float,
    frame_reference: str,
    algorithm_version: str = CV_ALGORITHM_VERSION,
) -> dict:
    if not event_id or not event_id.strip():
        raise ValueError("event_id é obrigatório")

    class_percentage = float(detector_result["class_percentage"])
    if not 0.0 <= class_percentage <= 100.0:
        raise ValueError("class_percentage deve estar na escala 0-100")

    payload = {
        "event_id": event_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "area_id": area_id,
        "source": source,
        "detected_class": detector_result["detected_class"],
        "class_percentage": class_percentage,
        "change_score": change_score,
        "cloud_score": quality_result["cloud_score"],
        "shadow_score": quality_result["shadow_score"],
        "brightness_score": quality_result["brightness_score"],
        "blur_score": quality_result["blur_score"],
        "image_quality": quality_result["image_quality"],
        "cv_confidence": quality_result["cv_confidence"],
        "frame_reference": frame_reference,
        "algorithm_version": algorithm_version,
    }

    missing = [f for f in _REQUIRED_FIELDS if payload.get(f) is None]
    if missing:
        raise ValueError(f"Campos obrigatórios ausentes: {missing}")

    return IoTPayload.model_validate(payload).model_dump()
