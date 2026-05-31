from pathlib import Path

import cv2
import numpy as np
import pytest
from pydantic import ValidationError

from iot.change_detector import compute_change_score
from iot.contract import IOT_PAYLOAD_REQUIRED_FIELDS, IoTPayload
from iot.detector import detect_class
from iot.pipeline import run_pipeline
from iot.quality import compute_quality_metrics


def _solid_bgr(b: int, g: int, r: int, size: int = 64) -> np.ndarray:
    return np.full((size, size, 3), (b, g, r), dtype=np.uint8)


def _write_fixture_frame(path: Path, b: int, g: int, r: int) -> None:
    frame = _solid_bgr(b, g, r)
    frame[0:4, 0:4] = (255, 255, 255)
    frame[4:8, 0:4] = (0, 0, 0)
    cv2.imwrite(str(path), frame)


@pytest.mark.parametrize(
    ("expected_class", "frame"),
    [
        ("vegetacao", _solid_bgr(50, 150, 50)),
        ("solo_exposto", _solid_bgr(80, 100, 130)),
        ("agua", _solid_bgr(150, 100, 50)),
        ("queimada", _solid_bgr(20, 20, 20)),
        ("baixa_visibilidade", _solid_bgr(200, 200, 200)),
    ],
)
def test_synthetic_detector_gate_supports_all_classes(expected_class, frame):
    result = detect_class(frame)

    assert result["detected_class"] == expected_class
    assert 0.0 <= result["class_percentage"] <= 100.0
    assert result["class_percentage"] >= 90.0


def test_change_score_gate_limits_for_identical_and_opposite_frames():
    frame = _solid_bgr(90, 120, 60)
    black = _solid_bgr(0, 0, 0)
    white = _solid_bgr(255, 255, 255)

    assert compute_change_score(frame, frame.copy()) <= 0.01
    assert compute_change_score(black, white) >= 0.90


def test_quality_and_pipeline_scores_stay_normalized(tmp_path):
    _write_fixture_frame(tmp_path / "frame_2024-06-01.png", 40, 160, 50)
    _write_fixture_frame(tmp_path / "frame_2024-06-02.png", 80, 110, 150)

    quality = compute_quality_metrics(_solid_bgr(40, 160, 50))
    for field in ("cloud_score", "shadow_score", "brightness_score", "blur_score", "cv_confidence"):
        assert 0.0 <= quality[field] <= 1.0

    payloads = run_pipeline(str(tmp_path), "area-gate-001", "Sentinel-2")

    assert len(payloads) >= 1
    payload = payloads[0]
    for field in IOT_PAYLOAD_REQUIRED_FIELDS:
        assert field in payload
        assert payload[field] not in (None, "")

    for field in ("change_score", "cloud_score", "shadow_score", "brightness_score", "blur_score", "cv_confidence"):
        assert 0.0 <= payload[field] <= 1.0
    assert 0.0 <= payload["class_percentage"] <= 100.0
    assert IoTPayload.model_validate(payload).event_id == payload["event_id"]


def test_iot_payload_validator_rejects_missing_required_field(tmp_path):
    _write_fixture_frame(tmp_path / "frame_2024-06-01.png", 40, 160, 50)
    _write_fixture_frame(tmp_path / "frame_2024-06-02.png", 80, 110, 150)
    payload = run_pipeline(str(tmp_path), "area-gate-001", "Sentinel-2")[0]
    del payload["source"]

    with pytest.raises(ValidationError):
        IoTPayload.model_validate(payload)
