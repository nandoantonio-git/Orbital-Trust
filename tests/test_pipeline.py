import cv2
import numpy as np
import pytest

from iot.pipeline import run_pipeline

_REQUIRED_FIELDS = (
    "event_id", "timestamp", "area_id", "source",
    "detected_class", "class_percentage", "change_score",
    "cloud_score", "shadow_score", "image_quality",
    "cv_confidence", "frame_reference",
)


def _write_frame(path: str, shade: int) -> None:
    """Write a 64x64 frame: mostly green + cloud/shadow pixels at a unique shade."""
    frame = np.full((64, 64, 3), [0, 100 + shade * 20, 0], dtype=np.uint8)
    # cloud pixels (all channels >= 200) — ensures cloud_score > 0
    frame[0, :8] = [255, 255, 255]
    # shadow pixels (all channels <= 50) — ensures shadow_score > 0
    frame[1, :8] = [0, 0, 0]
    cv2.imwrite(path, frame)


def test_run_pipeline_three_frames_two_payloads(tmp_path):
    for i in range(3):
        _write_frame(str(tmp_path / f"frame_{i+1:03d}.png"), shade=i + 1)

    payloads = run_pipeline(str(tmp_path), "area-test-001", "Sentinel-2")

    assert len(payloads) == 2
    for payload in payloads:
        for field in _REQUIRED_FIELDS:
            assert field in payload, f"Campo ausente: {field}"
            assert payload[field] not in (None, ""), f"Campo vazio: {field}"
        assert payload["area_id"] == "area-test-001"
        assert payload["source"] == "Sentinel-2"


def test_run_pipeline_missing_folder_raises():
    with pytest.raises(FileNotFoundError):
        run_pipeline("/tmp/nonexistent_folder_xyz", "area-x", "Sentinel-2")


def test_run_pipeline_empty_folder_returns_empty(tmp_path):
    assert run_pipeline(str(tmp_path), "area-x", "Sentinel-2") == []


def test_run_pipeline_single_frame_returns_empty(tmp_path):
    _write_frame(str(tmp_path / "frame_001.png"), shade=1)
    assert run_pipeline(str(tmp_path), "area-x", "Sentinel-2") == []
