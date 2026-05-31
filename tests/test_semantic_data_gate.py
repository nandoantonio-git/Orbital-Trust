import json
from pathlib import Path

import cv2
import numpy as np

import scripts.semantic_data_gate as gate


def _write_frame(path: Path, color: tuple[int, int, int]) -> None:
    frame = np.zeros((32, 32, 3), dtype=np.uint8)
    frame[:, :] = color
    cv2.imwrite(str(path), frame)


def _payload(frame_reference: str, class_percentage: float = 42.0) -> dict:
    return {
        "event_id": "EVT-001",
        "timestamp": "2024-07-15T12:00:00Z",
        "area_id": "BR-MT-001",
        "source": "Sentinel-2",
        "detected_class": "vegetacao",
        "class_percentage": class_percentage,
        "change_score": 0.1,
        "cloud_score": 0.1,
        "shadow_score": 0.0,
        "brightness_score": 0.45,
        "blur_score": 0.2,
        "image_quality": "boa",
        "cv_confidence": 0.8,
        "frame_reference": frame_reference,
        "algorithm_version": "orbital-cv-v0.2.0",
        "tile_quality": {
            "black_ratio": 0.0,
            "date_used": "2024-07-15",
            "source": "Sentinel-2",
            "check_tile_integrity": {"passes": True, "black_ratio": 0.0, "reason": "ok"},
            "fallback": {"used": False},
            "class_percentage": class_percentage,
        },
    }


def _write_payloads(path: Path, payloads: list[dict]) -> None:
    path.write_text(json.dumps(payloads), encoding="utf-8")


def test_payload_gate_fails_black_tile_without_fallback(tmp_path):
    _write_frame(tmp_path / "frame_a.jpg", (120, 120, 120))
    _write_frame(tmp_path / "frame_black.jpg", (0, 0, 0))
    path = tmp_path / "payloads_test.json"
    _write_payloads(path, [_payload("frame_a.jpg>frame_black.jpg")])

    errors = gate.validate_payload_file(path, tmp_path)

    assert any("black_ratio=1.00 without fallback" in error for error in errors)


def test_payload_gate_accepts_valid_local_frame(tmp_path):
    _write_frame(tmp_path / "frame_a.jpg", (120, 120, 120))
    _write_frame(tmp_path / "frame_b.jpg", (80, 160, 80))
    path = tmp_path / "payloads_test.json"
    _write_payloads(path, [_payload("frame_a.jpg>frame_b.jpg")])

    assert gate.validate_payload_file(path, tmp_path) == []


def test_mock_gate_fails_gibs_url_with_contract_source():
    alerts = [
        {
            "event_id": f"EVT-{index}",
            "timestamp": "2024-07-15T12:00:00Z",
            "detected_class": detected_class,
            "risk_level": risk_level,
            "analysis_confidence": 0.8,
            "explanation": "ok",
            "recommendation": "ok",
            "model_version": "orbital-ml-v1.2.0",
            "class_percentage": 40.0,
            "change_score": 0.2,
            "source": "MODIS/GIBS",
            "visual_product": gate.GIBS_VISUAL_PRODUCT,
            "tile_provider": gate.GIBS_TILE_PROVIDER,
            "image_url": (
                "https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/"
                "MODIS_Terra_CorrectedReflectance_TrueColor/default/2024-07-15/250m/7/29/42.jpg"
            ),
        }
        for index, (detected_class, risk_level) in enumerate(
            [
                ("vegetacao", "baixo"),
                ("solo_exposto", "medio"),
                ("agua", "alto"),
                ("queimada", "medio"),
                ("vegetacao", "baixo"),
            ],
            start=1,
        )
    ]
    alerts[0]["source"] = "Sentinel-2"

    errors = gate.validate_mock_alerts(alerts)

    assert any("incoherent with verifiable URL source 'MODIS/GIBS'" in error for error in errors)


def test_versioned_data_gate_passes_current_artifacts():
    assert gate.validate_all(Path(".")) == []
