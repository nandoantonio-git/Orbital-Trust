import json
import os
from typing import List
from unittest.mock import patch

import numpy as np
import cv2
import pytest

from iot.orbital_ingestion import run_orbital_ingestion


_MOCK_STAC_RESPONSE = {
    "type": "FeatureCollection",
    "features": [
        {
            "id": "S2A_MSIL2A_20240115",
            "type": "Feature",
            "properties": {
                "datetime": "2024-01-15T10:30:00Z",
                "eo:cloud_cover": 5.2,
            },
            "assets": {
                "thumbnail": {"href": "https://example.com/thumb1.jpg"},
            },
        },
        {
            "id": "S2B_MSIL2A_20240120",
            "type": "Feature",
            "properties": {
                "datetime": "2024-01-20T11:00:00Z",
                "eo:cloud_cover": 10.0,
            },
            "assets": {
                "thumbnail": {"href": "https://example.com/thumb2.jpg"},
            },
        },
    ],
}


def _write_two_frames(frames_dir: str) -> None:
    """Write two valid synthetic PNG frames so run_pipeline produces a payload.

    Top quarter: white pixels → non-zero cloud_score.
    Bottom quarter: black pixels → non-zero shadow_score.
    Middle: mid-range, slightly different between frames → non-zero change_score.
    PNG avoids JPEG compression shifting pixels across threshold boundaries.
    """
    os.makedirs(frames_dir, exist_ok=True)

    def _make_frame(mid_val: int) -> np.ndarray:
        h, w = 64, 64
        frame = np.full((h, w, 3), mid_val, dtype=np.uint8)
        frame[: h // 4, :] = 255   # cloud band
        frame[3 * h // 4 :, :] = 0  # shadow band
        return frame

    frame_a = _make_frame(100)
    frame_b = _make_frame(130)
    cv2.imwrite(os.path.join(frames_dir, "frame_a.png"), frame_a)
    cv2.imwrite(os.path.join(frames_dir, "frame_b.png"), frame_b)


def _mock_download(manifest_path: str, frames_dir: str) -> List[str]:
    _write_two_frames(frames_dir)
    return [
        os.path.join(frames_dir, "frame_a.jpg"),
        os.path.join(frames_dir, "frame_b.jpg"),
    ]


def test_run_orbital_ingestion_returns_list():
    result = run_orbital_ingestion(
        area_id="area-001",
        bbox=[-46.0, -23.0, -45.0, -22.0],
        start_date="2024-01-01",
        end_date="2024-01-31",
        source="Sentinel-2",
        _mock_stac_response=_MOCK_STAC_RESPONSE,
        _mock_download=_mock_download,
    )
    assert isinstance(result, list)


def test_run_orbital_ingestion_payloads_have_required_fields():
    result = run_orbital_ingestion(
        area_id="area-002",
        bbox=[-46.0, -23.0, -45.0, -22.0],
        start_date="2024-01-01",
        end_date="2024-01-31",
        source="Sentinel-2",
        _mock_stac_response=_MOCK_STAC_RESPONSE,
        _mock_download=_mock_download,
    )
    required = {
        "event_id", "timestamp", "area_id", "source", "detected_class",
        "class_percentage", "change_score", "cloud_score", "shadow_score",
        "image_quality", "cv_confidence", "frame_reference",
    }
    for payload in result:
        for field in required:
            assert field in payload, f"Campo obrigatório ausente: {field}"


def test_run_orbital_ingestion_source_is_preserved():
    result = run_orbital_ingestion(
        area_id="area-003",
        bbox=[-46.0, -23.0, -45.0, -22.0],
        start_date="2024-01-01",
        end_date="2024-01-31",
        source="Sentinel-2",
        _mock_stac_response=_MOCK_STAC_RESPONSE,
        _mock_download=_mock_download,
    )
    for payload in result:
        assert payload["source"] == "Sentinel-2"


def test_run_orbital_ingestion_empty_stac_returns_empty():
    result = run_orbital_ingestion(
        area_id="area-004",
        bbox=[-46.0, -23.0, -45.0, -22.0],
        start_date="2024-01-01",
        end_date="2024-01-31",
        source="Landsat",
        _mock_stac_response={"type": "FeatureCollection", "features": []},
        _mock_download=_mock_download,
    )
    assert result == []


def test_run_orbital_ingestion_invalid_source_raises():
    with pytest.raises(ValueError, match="source deve ser um de"):
        run_orbital_ingestion(
            area_id="area-005",
            bbox=[-46.0, -23.0, -45.0, -22.0],
            start_date="2024-01-01",
            end_date="2024-01-31",
            source="InvalidSource",
            _mock_stac_response=_MOCK_STAC_RESPONSE,
            _mock_download=_mock_download,
        )


def test_run_orbital_ingestion_area_id_in_payloads():
    result = run_orbital_ingestion(
        area_id="my-area",
        bbox=[-46.0, -23.0, -45.0, -22.0],
        start_date="2024-01-01",
        end_date="2024-01-31",
        source="INPE",
        _mock_stac_response=_MOCK_STAC_RESPONSE,
        _mock_download=_mock_download,
    )
    for payload in result:
        assert payload["area_id"] == "my-area"
