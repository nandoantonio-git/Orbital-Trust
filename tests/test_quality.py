import numpy as np
from iot.quality import compute_quality_metrics


def _solid_bgr(b: int, g: int, r: int, size: int = 10) -> np.ndarray:
    frame = np.full((size, size, 3), (b, g, r), dtype=np.uint8)
    return frame


def test_white_frame_high_cloud():
    result = compute_quality_metrics(_solid_bgr(255, 255, 255))
    assert result["cloud_score"] == 1.0
    assert result["shadow_score"] == 0.0
    assert result["image_quality"] == 0.0
    for k in ("cloud_score", "shadow_score", "image_quality", "cv_confidence"):
        assert 0.0 <= result[k] <= 1.0


def test_black_frame_high_shadow():
    result = compute_quality_metrics(_solid_bgr(0, 0, 0))
    assert result["shadow_score"] == 1.0
    assert result["cloud_score"] == 0.0
    assert result["image_quality"] == 0.0
    for k in ("cloud_score", "shadow_score", "image_quality", "cv_confidence"):
        assert 0.0 <= result[k] <= 1.0


def test_colorful_frame_good_quality():
    result = compute_quality_metrics(_solid_bgr(0, 200, 0))
    assert result["cloud_score"] == 0.0
    assert result["shadow_score"] == 0.0
    assert result["image_quality"] == 1.0
    for k in ("cloud_score", "shadow_score", "image_quality", "cv_confidence"):
        assert 0.0 <= result[k] <= 1.0


def test_return_schema():
    result = compute_quality_metrics(_solid_bgr(100, 100, 100))
    for k in ("cloud_score", "shadow_score", "image_quality", "cv_confidence"):
        assert k in result
        assert isinstance(result[k], float)
        assert 0.0 <= result[k] <= 1.0
