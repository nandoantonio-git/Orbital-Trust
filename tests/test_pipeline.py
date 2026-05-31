import json

import cv2
import numpy as np
import pytest
from unittest.mock import patch

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


def test_run_pipeline_black_frame_a_colored_frame_b_yields_one_payload(tmp_path):
    """1 black tile (frame_a) + 1 colored tile (frame_b) → 1 payload for the colored tile."""
    black = np.zeros((64, 64, 3), dtype=np.uint8)
    cv2.imwrite(str(tmp_path / "frame_001.png"), black)
    _write_frame(str(tmp_path / "frame_002.png"), shade=1)

    payloads = run_pipeline(str(tmp_path), "area-test", "Sentinel-2")

    assert len(payloads) == 1
    assert "tile_quality" in payloads[0]
    assert isinstance(payloads[0]["tile_quality"]["black_ratio"], float)
    assert isinstance(payloads[0]["tile_quality"]["date_used"], str)


def test_run_pipeline_black_frame_b_skipped_when_fetch_returns_none(tmp_path):
    """Black frame_b that cannot be replaced is skipped → 0 payloads."""
    _write_frame(str(tmp_path / "a_frame.png"), shade=1)
    black = np.zeros((64, 64, 3), dtype=np.uint8)
    cv2.imwrite(str(tmp_path / "z_frame_20240601.png"), black)

    with patch("iot.pipeline.fetch_best_tile", return_value=(None, None)):
        payloads = run_pipeline(
            str(tmp_path),
            "area-test",
            "Sentinel-2",
            url_templates={"z_frame_20240601.png": "https://example.com/{date}/tile.png"},
        )

    assert len(payloads) == 0


def test_run_pipeline_black_remote_frame_b_replaced_by_alt(tmp_path):
    """Black remote frame_b replaced by fetch alt → payload tracks date and URL."""
    _write_frame(str(tmp_path / "a_frame.png"), shade=1)
    black = np.zeros((64, 64, 3), dtype=np.uint8)
    cv2.imwrite(str(tmp_path / "z_frame_20240601.png"), black)

    alt_frame = np.full((64, 64, 3), 200, dtype=np.uint8)
    url_template = "https://example.com/tiles/{date}/tile.png"
    with patch("iot.pipeline.fetch_best_tile", return_value=(alt_frame, "2024-06-03")) as fetch:
        payloads = run_pipeline(
            str(tmp_path),
            "area-test",
            "Sentinel-2",
            url_templates={"z_frame_20240601.png": url_template},
        )

    fetch.assert_called_once_with(url_template, "2024-06-01")
    assert len(payloads) == 1
    assert ">alt:2024-06-03" in payloads[0]["frame_reference"]
    tq = payloads[0]["tile_quality"]
    assert tq["date_used"] == "2024-06-03"
    assert tq["url_used"] == "https://example.com/tiles/2024-06-03/tile.png"
    assert tq["source"] == "Sentinel-2"
    assert tq["check_tile_integrity"]["passes"] is True
    assert tq["detected_class"] == payloads[0]["detected_class"]
    assert tq["class_percentage"] == payloads[0]["class_percentage"]
    assert tq["fallback"]["used"] is True
    assert tq["fallback"]["original_rejected"]["filename"] == "z_frame_20240601.png"
    assert tq["fallback"]["original_rejected"]["check_tile_integrity"]["passes"] is False
    assert tq["fallback"]["alternative_used"]["url"] == "https://example.com/tiles/2024-06-03/tile.png"
    assert tq["fallback"]["alternative_used"]["date_used"] == "2024-06-03"


def test_run_pipeline_loads_remote_template_from_frame_sources(tmp_path):
    """Remote metadata sidecar lets pipeline derive the date template."""
    _write_frame(str(tmp_path / "a_frame.png"), shade=1)
    black = np.zeros((64, 64, 3), dtype=np.uint8)
    cv2.imwrite(str(tmp_path / "z_frame_20240601.png"), black)
    (tmp_path / "frame_sources.json").write_text(json.dumps({
        "z_frame_20240601.png": {
            "source": "MODIS/GIBS",
            "url": "https://example.com/tiles/2024-06-01/tile.png",
            "row": 12,
            "col": 34,
            "bbox": [-54.0, -12.0, -52.0, -10.0],
        },
    }))

    alt_frame = np.full((64, 64, 3), 200, dtype=np.uint8)
    with patch("iot.pipeline.fetch_best_tile", return_value=(alt_frame, "2024-06-02")) as fetch:
        payloads = run_pipeline(str(tmp_path), "area-test", "Sentinel-2")

    fetch.assert_called_once_with("https://example.com/tiles/{date}/tile.png", "2024-06-01")
    assert len(payloads) == 1
    tq = payloads[0]["tile_quality"]
    assert tq["url_used"] == "https://example.com/tiles/2024-06-02/tile.png"
    assert tq["source"] == "MODIS/GIBS"
    assert tq["fallback"]["original_rejected"]["source"] == "MODIS/GIBS"
    assert tq["fallback"]["alternative_used"]["source"] == "MODIS/GIBS"
    assert tq["fallback"]["original_rejected"]["row"] == 12
    assert tq["fallback"]["original_rejected"]["col"] == 34
    assert tq["fallback"]["original_rejected"]["bbox"] == [-54.0, -12.0, -52.0, -10.0]
    assert tq["fallback"]["alternative_used"]["row"] == 12
    assert tq["fallback"]["alternative_used"]["col"] == 34
    assert tq["fallback"]["alternative_used"]["bbox"] == [-54.0, -12.0, -52.0, -10.0]


def test_run_pipeline_compact_date_invalid_frame_replaced_by_local_alt(tmp_path):
    """Invalid 20240601 frame is replaced by a local compact-date tile from 20240603."""
    _write_frame(str(tmp_path / "frame_mt_20240603.jpg"), shade=1)
    black = np.zeros((64, 64, 3), dtype=np.uint8)
    cv2.imwrite(str(tmp_path / "z_frame_mt_20240601.jpg"), black)

    payloads = run_pipeline(str(tmp_path), "area-test", "Sentinel-2")

    assert len(payloads) == 1
    assert ">alt:2024-06-03" in payloads[0]["frame_reference"]
    assert payloads[0]["tile_quality"]["date_used"] == "2024-06-03"
    assert payloads[0]["tile_quality"]["black_ratio"] <= 0.15
    assert payloads[0]["tile_quality"]["fallback"]["used"] is True
    assert payloads[0]["tile_quality"]["fallback"]["original_rejected"]["filename"] == "z_frame_mt_20240601.jpg"
    assert payloads[0]["tile_quality"]["fallback"]["alternative_used"]["filename"] == "frame_mt_20240603.jpg"


def test_run_pipeline_compact_date_invalid_frame_without_local_alt_is_skipped(tmp_path):
    """Invalid compact-date frame without a local alternative is skipped without raising."""
    _write_frame(str(tmp_path / "frame_mt_20240520.jpg"), shade=1)
    black = np.zeros((64, 64, 3), dtype=np.uint8)
    cv2.imwrite(str(tmp_path / "z_frame_mt_20240601.jpg"), black)

    with patch("iot.pipeline.fetch_best_tile") as fetch:
        payloads = run_pipeline(str(tmp_path), "area-test", "Sentinel-2")

    assert payloads == []
    fetch.assert_not_called()


def test_run_pipeline_payload_includes_tile_quality(tmp_path):
    """All payloads include tile_quality with black_ratio and date_used."""
    for i in range(2):
        _write_frame(str(tmp_path / f"frame_{i+1:03d}.png"), shade=i + 1)

    payloads = run_pipeline(str(tmp_path), "area-test", "Sentinel-2")

    assert len(payloads) == 1
    tq = payloads[0]["tile_quality"]
    assert "black_ratio" in tq
    assert "date_used" in tq
    assert "check_tile_integrity" in tq
    assert "selected_tile" in tq
    assert "fallback" in tq
    assert "detected_class" in tq
    assert "class_percentage" in tq
    assert isinstance(tq["black_ratio"], float)
    assert isinstance(tq["date_used"], str)
    assert tq["date_used"] == "2000-01-01"
    assert tq["fallback"]["used"] is False
