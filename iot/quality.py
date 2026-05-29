import numpy as np


def compute_quality_metrics(frame: np.ndarray) -> dict:
    """Return cloud_score, shadow_score, image_quality, cv_confidence for a BGR frame."""
    total = frame.shape[0] * frame.shape[1]
    if total == 0:
        return {"cloud_score": 0.0, "shadow_score": 0.0, "image_quality": 1.0, "cv_confidence": 0.0}

    # Cloud: pixels close to white (all channels >= 200)
    cloud_mask = np.all(frame >= 200, axis=2)
    cloud_score = float(np.count_nonzero(cloud_mask)) / total

    # Shadow: pixels close to black (all channels <= 50)
    shadow_mask = np.all(frame <= 50, axis=2)
    shadow_score = float(np.count_nonzero(shadow_mask)) / total

    image_quality = 1.0 - max(cloud_score, shadow_score)

    # cv_confidence: high when image_quality is high, penalised by noise (std of grayscale)
    gray = frame.mean(axis=2)
    std_norm = float(gray.std()) / 255.0
    cv_confidence = round(min(1.0, image_quality * (0.5 + 0.5 * std_norm)), 4)

    return {
        "cloud_score": round(cloud_score, 4),
        "shadow_score": round(shadow_score, 4),
        "image_quality": round(image_quality, 4),
        "cv_confidence": cv_confidence,
    }
