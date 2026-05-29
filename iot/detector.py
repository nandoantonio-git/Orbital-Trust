from typing import Any, Dict

import cv2
import numpy as np

# HSV ranges (OpenCV: H 0-179, S 0-255, V 0-255)
_HSV_RANGES: Dict[str, list] = {
    "baixa_visibilidade": [((0,   0,  150), (179,  40, 255))],  # low saturation, bright
    "queimada":           [((0,   0,    0), (179, 255,  50))],  # very dark (charred)
    "agua":               [((90, 40,   30), (130, 255, 255))],  # blue hues
    "vegetacao":          [((35, 40,   40), (85,  255, 255))],  # green hues
    "solo_exposto":       [((10, 30,   50), (30,  220, 255))],  # brown/tan hues
}


def detect_class(frame: np.ndarray) -> Dict[str, Any]:
    """Return dominant environmental class and its pixel coverage fraction."""
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    total = frame.shape[0] * frame.shape[1]

    counts: Dict[str, int] = {}
    for cls, ranges in _HSV_RANGES.items():
        mask = np.zeros(frame.shape[:2], dtype=np.uint8)
        for lo, hi in ranges:
            mask |= cv2.inRange(hsv, np.array(lo, dtype=np.uint8), np.array(hi, dtype=np.uint8))
        counts[cls] = int(np.count_nonzero(mask))

    dominant = max(counts, key=lambda c: counts[c]) if any(counts.values()) else "baixa_visibilidade"
    pct = counts[dominant] / total if total > 0 else 0.0

    return {
        "detected_class": dominant,
        "class_percentage": round(float(pct), 4),
    }
