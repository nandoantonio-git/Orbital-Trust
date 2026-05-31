from typing import Any, Dict

import numpy as np


def _validate_bgr_frame(frame: np.ndarray) -> None:
    if not isinstance(frame, np.ndarray):
        raise ValueError("frame must be a numpy ndarray")
    if frame.size == 0:
        raise ValueError("frame must not be empty")
    if frame.ndim != 3 or frame.shape[2] != 3:
        raise ValueError("frame must have shape (height, width, 3) in BGR order")
    if not np.issubdtype(frame.dtype, np.number):
        raise ValueError("frame must contain numeric pixel values")


def detect_class(frame: np.ndarray) -> Dict[str, Any]:
    """Return the dominant MODIS class and its area percentage on a 0-100 scale."""
    _validate_bgr_frame(frame)

    b = frame[:, :, 0].astype(float)
    g = frame[:, :, 1].astype(float)
    r = frame[:, :, 2].astype(float)

    mean_px = (b + g + r) / 3.0
    # Per-pixel channel spread separates bright neutral haze from surface colors.
    std_px = np.sqrt(((b - mean_px) ** 2 + (g - mean_px) ** 2 + (r - mean_px) ** 2) / 3.0)

    # MODIS true-color frames arrive through OpenCV as BGR.
    bv = (mean_px > 160) & (std_px < 20)
    remaining = ~bv

    q = remaining & (mean_px < 40)
    remaining &= ~q

    a = remaining & (b > r * 1.05) & (b > g * 1.05) & (mean_px > 30)
    remaining &= ~a

    v = remaining & (g > r * 1.02) & (g > b * 1.02) & (mean_px > 30) & (mean_px < 160)
    remaining &= ~v

    s = remaining & (r >= g) & (r > b * 1.1) & (mean_px > 50)

    counts: Dict[str, int] = {
        "baixa_visibilidade": int(np.count_nonzero(bv)),
        "queimada": int(np.count_nonzero(q)),
        "agua": int(np.count_nonzero(a)),
        "vegetacao": int(np.count_nonzero(v)),
        "solo_exposto": int(np.count_nonzero(s)),
    }

    dominant = max(counts, key=lambda c: counts[c])
    total = frame.shape[0] * frame.shape[1]
    pct = (counts[dominant] / total * 100.0) if total > 0 else 0.0

    return {
        "detected_class": dominant,
        "class_percentage": round(float(pct), 2),
    }
