"""Feature extraction: IoTPayload → numpy array para o classificador."""

from __future__ import annotations

from typing import Any

import numpy as np

DETECTED_CLASSES = ["vegetacao", "solo_exposto", "agua", "queimada", "baixa_visibilidade"]
SOURCES = ["Sentinel-2", "Landsat", "FIRMS", "INPE"]
IMAGE_QUALITY_ORDINAL = {"baixa": 0.0, "media": 0.5, "boa": 1.0}

FEATURE_NAMES = (
    ["class_percentage", "change_score", "cloud_score", "shadow_score",
     "brightness_score", "blur_score", "cv_confidence", "image_quality_ord"]
    + [f"class_{c}" for c in DETECTED_CLASSES]
    + [f"source_{s}" for s in SOURCES]
)


def extract_features(payload: Any) -> np.ndarray:
    """Converte IoTPayload (ou dict) em vetor de 16 features."""
    if hasattr(payload, "model_dump"):
        data: dict = payload.model_dump()
    else:
        data = dict(payload)

    numeric = [
        data["class_percentage"] / 100.0,
        data["change_score"],
        data["cloud_score"],
        data["shadow_score"],
        data["brightness_score"],
        data["blur_score"],
        data["cv_confidence"],
        IMAGE_QUALITY_ORDINAL[data["image_quality"]],
    ]

    class_onehot = [1.0 if data["detected_class"] == c else 0.0 for c in DETECTED_CLASSES]
    source_onehot = [1.0 if data["source"] == s else 0.0 for s in SOURCES]

    return np.array(numeric + class_onehot + source_onehot, dtype=np.float32)
