import sys
from typing import Any, Dict


FALLBACK_CONFIDENCE_CAP = 0.2

_FALLBACK_DETECTOR_RESULT = {
    "detected_class": "baixa_visibilidade",
    "class_percentage": 0.0,
}

_FALLBACK_QUALITY_RESULT = {
    "cloud_score": 0.0,
    "shadow_score": 0.0,
    "brightness_score": 0.0,
    "blur_score": 1.0,
    "image_quality": "baixa",
    "cv_confidence": 0.0,
}


def fallback_detector_result() -> Dict[str, Any]:
    return dict(_FALLBACK_DETECTOR_RESULT)


def fallback_quality_result() -> Dict[str, Any]:
    return dict(_FALLBACK_QUALITY_RESULT)


def penalize_quality_for_fallback(quality_result: Dict[str, Any]) -> Dict[str, Any]:
    quality = {**fallback_quality_result(), **quality_result}
    try:
        confidence = float(quality.get("cv_confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0

    quality["image_quality"] = "baixa"
    quality["cv_confidence"] = round(max(0.0, min(confidence, FALLBACK_CONFIDENCE_CAP)), 4)
    return quality


def log_visual_inference_error(component: str, frame_reference: str, exc: Exception) -> None:
    safe_frame = str(frame_reference).replace("\n", " ")[:120]
    safe_message = str(exc).replace("\n", " ")[:180]
    print(
        "[visual_fallback] "
        f"component={component} frame={safe_frame} "
        f"error={type(exc).__name__}: {safe_message}",
        file=sys.stderr,
    )
