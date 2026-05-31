import numpy as np


def compute_quality_metrics(frame: np.ndarray) -> dict:
    """Return normalized visual scores and categorical image quality for a BGR frame."""
    total = frame.shape[0] * frame.shape[1]
    if total == 0:
        return {
            "cloud_score": 0.0,
            "shadow_score": 0.0,
            "brightness_score": 0.0,
            "blur_score": 1.0,
            "image_quality": "baixa",
            "cv_confidence": 0.0,
        }

    # Cloud: pixels close to white (all channels >= 200)
    cloud_mask = np.all(frame >= 200, axis=2)
    cloud_score = float(np.count_nonzero(cloud_mask)) / total

    # Shadow: pixels close to black (all channels <= 50)
    shadow_mask = np.all(frame <= 50, axis=2)
    shadow_score = float(np.count_nonzero(shadow_mask)) / total

    gray = frame.mean(axis=2)
    brightness_score = float(gray.mean()) / 255.0

    vertical = float(np.abs(np.diff(gray, axis=0)).mean()) if gray.shape[0] > 1 else 0.0
    horizontal = float(np.abs(np.diff(gray, axis=1)).mean()) if gray.shape[1] > 1 else 0.0
    sharpness_score = min(1.0, ((vertical + horizontal) / 2.0) / 32.0)
    blur_score = 1.0 - sharpness_score

    brightness_penalty = max(0.0, 0.18 - brightness_score) * 0.5
    brightness_penalty += max(0.0, brightness_score - 0.88) * 0.5
    quality_score = 1.0 - max(cloud_score, shadow_score)
    quality_score = max(0.0, min(1.0, quality_score - brightness_penalty - (blur_score * 0.15)))

    if quality_score >= 0.75:
        image_quality = "boa"
    elif quality_score >= 0.45:
        image_quality = "media"
    else:
        image_quality = "baixa"

    std_norm = float(gray.std()) / 255.0
    cv_confidence = round(min(1.0, quality_score * (0.5 + 0.5 * std_norm)), 4)

    return {
        "cloud_score": round(cloud_score, 4),
        "shadow_score": round(shadow_score, 4),
        "brightness_score": round(brightness_score, 4),
        "blur_score": round(blur_score, 4),
        "image_quality": image_quality,
        "cv_confidence": cv_confidence,
    }
