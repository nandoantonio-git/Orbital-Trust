import sys
from unittest.mock import patch, MagicMock
from pathlib import Path

import cv2
import numpy as np
import pytest

sys.path.insert(0, "/workspace")
from api.main import derive_risk_level
import scripts.generate_mock_data as gmd
from iot.quality import compute_quality_metrics


def _encode_png(frame: np.ndarray) -> bytes:
    _, buf = cv2.imencode(".png", frame)
    return bytes(buf)


def _green_frame(size: int = 64) -> np.ndarray:
    # BGR(0,200,0) → green channel dominance → "vegetacao"
    f = np.zeros((size, size, 3), dtype=np.uint8)
    f[:, :] = (0, 200, 0)
    return f


def _dark_frame(size: int = 64) -> np.ndarray:
    # BGR(20,20,20) → very dark → "queimada"
    return np.full((size, size, 3), 20, dtype=np.uint8)


def _tan_frame(size: int = 64) -> np.ndarray:
    # BGR approx brown/tan → red channel dominance → "solo_exposto"
    f = np.zeros((size, size, 3), dtype=np.uint8)
    f[:, :] = (30, 100, 180)  # BGR
    return f


def _alert(event_id: str, detected_class: str, risk_level: str) -> dict:
    return {
        "event_id": event_id,
        "timestamp": "2024-07-09T12:00:00Z",
        "detected_class": detected_class,
        "risk_level": risk_level,
        "analysis_confidence": 0.8,
        "explanation": "Análise orbital completada.",
        "recommendation": "Monitorar área.",
        "model_version": "orbital-ml-v1.2.0",
        "class_percentage": 42.0,
        "change_score": 0.2,
        "cloud_score": 0.1,
        "shadow_score": 0.0,
        "brightness_score": 0.45,
        "blur_score": 0.2,
        "image_quality": "boa",
        "cv_confidence": 0.8,
        "algorithm_version": "orbital-cv-v0.2.0",
        "source": "Sentinel-2",
        "contract_source": "Sentinel-2",
        "visual_product": "Sentinel-2",
        "tile_provider": "",
        "image_url": "https://example.com/tile.jpg",
    }


def test_generate_mock_data_delegates_final_risk_to_api_ml():
    source = Path("scripts/generate_mock_data.py").read_text(encoding="utf-8")

    assert "def derive_risk_level" not in source
    assert "analyze_alert(" in source


def test_build_previous_frame_for_risk_produces_expected_thresholds():
    curr = _green_frame()
    quality = compute_quality_metrics(curr)

    for target_risk in ("baixo", "medio", "alto"):
        change_score = gmd.compute_change_score(
            gmd.build_previous_frame_for_risk(curr, target_risk),
            curr,
        )
        assert (
            derive_risk_level(
                change_score=change_score,
                detected_class="vegetacao",
                image_quality=quality["image_quality"],
                cv_confidence=quality["cv_confidence"],
            )
            == target_risk
        )


# ── build_alert_from_frames ────────────────────────────────────────────────────

def test_build_alert_detected_class_matches_cv_pipeline():
    curr = _green_frame()
    prev = _green_frame()

    result = gmd.build_alert_from_frames(
        curr_frame=curr,
        prev_frame=prev,
        image_url="https://example.com/tile.jpg",
        date="2024-07-09",
        area_id="area-para",
        source="Sentinel-2",
        event_index=1,
    )

    assert result["detected_class"] == "vegetacao"


def test_build_alert_class_percentage_comes_from_detect_class():
    curr = _green_frame(size=64)
    prev = _green_frame(size=64)

    result = gmd.build_alert_from_frames(
        curr_frame=curr,
        prev_frame=prev,
        image_url="https://example.com/tile.jpg",
        date="2024-07-09",
        area_id="area-para",
        source="Sentinel-2",
        event_index=1,
    )

    # Should be expressed as percentage (0-100), not decimal (0-1)
    assert 0 <= result["class_percentage"] <= 100
    assert result["class_percentage"] == 100.0
    assert isinstance(result["class_percentage"], float)


def test_build_alert_risk_level_derived_from_change_score():
    curr = _green_frame(size=64)
    # Very different prev → high change_score → should produce a risk_level
    prev = np.full((64, 64, 3), 200, dtype=np.uint8)

    result = gmd.build_alert_from_frames(
        curr_frame=curr,
        prev_frame=prev,
        image_url="https://example.com/tile.jpg",
        date="2024-07-09",
        area_id="area-para",
        source="Sentinel-2",
        event_index=1,
    )

    assert result["risk_level"] in ("alto", "medio", "baixo")
    cs = result["change_score"]
    expected = derive_risk_level(
        change_score=cs,
        detected_class=result["detected_class"],
        image_quality=result["image_quality"],
        cv_confidence=result["cv_confidence"],
    )
    assert result["risk_level"] == expected


def test_build_alert_image_url_preserved():
    url = "https://gibs.earthdata.nasa.gov/test.jpg"
    result = gmd.build_alert_from_frames(
        curr_frame=_green_frame(),
        prev_frame=_green_frame(),
        image_url=url,
        date="2024-07-09",
        area_id="area-para",
        source="Sentinel-2",
        event_index=1,
    )
    assert result["image_url"] == url


def test_build_alert_has_all_required_alert_response_fields():
    result = gmd.build_alert_from_frames(
        curr_frame=_green_frame(),
        prev_frame=_green_frame(),
        image_url="https://example.com/t.jpg",
        date="2024-07-09",
        area_id="area-para",
        source="Sentinel-2",
        event_index=2,
    )

    for field in ("event_id", "timestamp", "detected_class", "risk_level",
                  "analysis_confidence", "explanation", "recommendation",
                  "model_version", "class_percentage", "change_score", "source",
                  "visual_product", "tile_provider", "image_url"):
        assert field in result, f"Missing field: {field}"


def test_build_alert_keeps_tile_quality_out_of_alert_response():
    result = gmd.build_alert_from_frames(
        curr_frame=_green_frame(),
        prev_frame=_green_frame(),
        image_url="https://example.com/t.jpg",
        date="2024-07-09",
        area_id="area-para",
        source="Sentinel-2",
        event_index=2,
    )

    assert "tile_quality" not in result


def test_build_alert_source_field_matches_input():
    result = gmd.build_alert_from_frames(
        curr_frame=_green_frame(),
        prev_frame=_green_frame(),
        image_url="https://example.com/t.jpg",
        date="2024-07-09",
        area_id="area-para",
        source="Landsat-8",
        event_index=1,
    )
    assert result["source"] == "Landsat-8"


def test_build_alert_gibs_url_uses_visual_source_metadata():
    result = gmd.build_alert_from_frames(
        curr_frame=_green_frame(),
        prev_frame=_green_frame(),
        image_url=(
            "https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/"
            "MODIS_Terra_CorrectedReflectance_TrueColor/default/2024-07-09/250m/7/29/42.jpg"
        ),
        date="2024-07-09",
        area_id="area-para",
        source="Sentinel-2",
        event_index=1,
    )

    assert result["source"] == gmd.GIBS_SOURCE
    assert result["visual_product"] == gmd.GIBS_VISUAL_PRODUCT
    assert result["tile_provider"] == gmd.GIBS_TILE_PROVIDER
    assert "Sentinel" not in result["explanation"]
    assert "Landsat" not in result["explanation"]


def test_build_alert_identical_frames_give_zero_change_score_and_baixo():
    frame = _green_frame()

    result = gmd.build_alert_from_frames(
        curr_frame=frame,
        prev_frame=frame.copy(),
        image_url="https://example.com/t.jpg",
        date="2024-07-09",
        area_id="area-para",
        source="Sentinel-2",
        event_index=1,
    )

    assert result["change_score"] == 0.0
    assert result["risk_level"] == "baixo"


# ── format_ts_file ─────────────────────────────────────────────────────────────

def test_format_ts_file_has_import_and_export():
    ts = gmd.format_ts_file([])
    assert "import" in ts
    assert "AlertResponse" in ts
    assert "export const generatedAlerts" in ts


def test_format_ts_file_contains_alert_values():
    alerts = [{
        "event_id": "EVT-2024-001",
        "timestamp": "2024-07-09T12:00:00Z",
        "detected_class": "vegetacao",
        "risk_level": "baixo",
        "analysis_confidence": 0.54,
        "explanation": "Vegetação densa detectada",
        "recommendation": "Monitorar rotina",
        "model_version": "orbital-ml-v1.2.0",
        "class_percentage": 65.5,
        "change_score": 0.18,
        "source": "Sentinel-2",
        "visual_product": "Sentinel-2",
        "tile_provider": "",
        "image_url": "https://gibs.earthdata.nasa.gov/test.jpg",
    }]
    ts = gmd.format_ts_file(alerts)

    assert "EVT-2024-001" in ts
    assert "vegetacao" in ts
    assert "baixo" in ts
    assert "https://gibs.earthdata.nasa.gov/test.jpg" in ts
    assert "Sentinel-2" in ts


def test_format_ts_file_contains_api_ml_contract_fields():
    ts = gmd.format_ts_file([_alert("EVT-001", "vegetacao", "baixo")])

    assert "cloud_score: 0.1" in ts
    assert "shadow_score: 0.0" in ts
    assert "brightness_score: 0.45" in ts
    assert "blur_score: 0.2" in ts
    assert "image_quality: 'boa'" in ts
    assert "cv_confidence: 0.8" in ts
    assert "algorithm_version: 'orbital-cv-v0.2.0'" in ts
    assert "contract_source: 'Sentinel-2'" in ts


def test_format_ts_file_valid_typescript_structure():
    alerts = [{
        "event_id": "EVT-001",
        "timestamp": "2024-09-02T12:00:00Z",
        "detected_class": "queimada",
        "risk_level": "medio",
        "analysis_confidence": 0.3,
        "explanation": "Test",
        "recommendation": "Test rec",
        "model_version": "orbital-ml-v1.2.0",
        "class_percentage": 52.77,
        "change_score": 0.326,
        "source": "Sentinel-2",
        "visual_product": "Sentinel-2",
        "tile_provider": "",
        "image_url": "https://example.com/tile.jpg",
    }]
    ts = gmd.format_ts_file(alerts)

    # Must have balanced brackets
    assert ts.count("[") == ts.count("]")
    assert ts.count("{") == ts.count("}")


def test_format_ts_file_does_not_export_internal_tile_quality():
    alert = _alert("EVT-001", "vegetacao", "baixo")
    alert["tile_quality"] = {"black_ratio": 0.01, "date_used": "2024-07-09"}
    alert["_tile_evidence"] = {"url": "https://example.com/tile.jpg", "black_ratio": 0.01}

    ts = gmd.format_ts_file([alert])

    assert "tile_quality" not in ts
    assert "black_ratio" not in ts
    assert "date_used" not in ts
    assert "_tile_evidence" not in ts


def test_build_mock_tile_evidence_keeps_debug_fields_outside_alert_response():
    alert = _alert("EVT-001", "vegetacao", "baixo")
    alert["source"] = gmd.GIBS_SOURCE
    alert["visual_product"] = gmd.GIBS_VISUAL_PRODUCT
    alert["tile_provider"] = gmd.GIBS_TILE_PROVIDER
    integrity = {"passes": True, "black_ratio": 0.02, "reason": "ok"}
    detector = {"detected_class": "vegetacao", "class_percentage": 65.5}

    evidence = gmd.build_mock_tile_evidence(
        alert=alert,
        area_id="area-para",
        row=29,
        col=42,
        date="2024-07-09",
        image_url=alert["image_url"],
        integrity=integrity,
        detector_result=detector,
    )

    assert evidence["event_id"] == "EVT-001"
    assert evidence["url"] == alert["image_url"]
    assert evidence["date_used"] == "2024-07-09"
    assert evidence["row"] == 29
    assert evidence["col"] == 42
    assert evidence["black_ratio"] == 0.02
    assert evidence["check_tile_integrity"] == integrity
    assert evidence["detected_class"] == "vegetacao"
    assert evidence["class_percentage"] == 65.5
    assert "tile_quality" not in alert


def test_write_mock_evidence_writes_debug_sidecar(tmp_path):
    output = tmp_path / "evidence.json"
    evidence = [{
        "event_id": "EVT-001",
        "url": "https://example.com/tile.jpg",
        "date_used": "2024-07-09",
        "row": 29,
        "col": 42,
        "black_ratio": 0.0,
        "check_tile_integrity": {"passes": True, "black_ratio": 0.0, "reason": "ok"},
        "detected_class": "vegetacao",
        "class_percentage": 100.0,
    }]

    gmd.write_mock_evidence(evidence, output)

    assert output.exists()
    assert "EVT-001" in output.read_text(encoding="utf-8")


# ── coverage validation ──────────────────────────────────────────────────────

def test_validate_minimum_coverage_accepts_required_volume_risks_and_classes():
    alerts = [
        _alert("EVT-001", "queimada", "alto"),
        _alert("EVT-002", "solo_exposto", "medio"),
        _alert("EVT-003", "vegetacao", "baixo"),
        _alert("EVT-004", "agua", "medio"),
        _alert("EVT-005", "vegetacao", "baixo"),
    ]
    alerts[0]["image_quality"] = "baixa"

    assert gmd.validate_minimum_coverage(alerts) == []


def test_validate_minimum_coverage_reports_clear_failures():
    alerts = [
        _alert("EVT-001", "queimada", "alto"),
        _alert("EVT-002", "solo_exposto", "alto"),
    ]

    errors = gmd.validate_minimum_coverage(alerts)

    assert any("expected at least 5 alerts" in error for error in errors)
    assert any("missing risk_level coverage" in error for error in errors)
    assert any("missing image_quality coverage" in error for error in errors)
    assert any("expected at least 4 detected classes" in error for error in errors)


def test_validate_minimum_coverage_rejects_gibs_url_with_contract_source():
    alerts = [
        _alert("EVT-001", "queimada", "alto"),
        _alert("EVT-002", "solo_exposto", "medio"),
        _alert("EVT-003", "vegetacao", "baixo"),
        _alert("EVT-004", "agua", "medio"),
        _alert("EVT-005", "vegetacao", "baixo"),
    ]
    alerts[0]["image_quality"] = "baixa"
    alerts[0]["image_url"] = (
        "https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/"
        "MODIS_Terra_CorrectedReflectance_TrueColor/default/2024-09-02/250m/7/37/44.jpg"
    )

    errors = gmd.validate_minimum_coverage(alerts)

    assert any("incoherent with MODIS/GIBS image_url" in error for error in errors)


def test_assert_minimum_coverage_fails_with_clear_message():
    with pytest.raises(ValueError, match="mock data coverage failed"):
        gmd.assert_minimum_coverage([])


def test_generated_mock_data_file_has_minimum_coverage():
    content = Path("mobile/src/services/generatedMockData.ts").read_text(encoding="utf-8")

    assert content.count("event_id:") >= 5
    assert "'baixo'" in content
    assert "'medio'" in content
    assert "'alto'" in content

    covered_classes = {
        cls
        for cls in gmd.ALLOWED_CLASSES
        if f"detected_class: '{cls}'" in content
    }
    assert len(covered_classes) >= 4


def test_generated_mock_data_file_has_coherent_gibs_metadata():
    content = Path("mobile/src/services/generatedMockData.ts").read_text(encoding="utf-8")

    assert "MODIS_Terra_CorrectedReflectance_TrueColor" in content
    assert "source: 'Sentinel-2'" not in content
    assert "source: 'Landsat'" not in content
    assert "source: 'MODIS/GIBS'" in content
    assert "visual_product: 'MODIS_Terra_CorrectedReflectance_TrueColor'" in content
    assert "tile_provider: 'NASA GIBS'" in content
    assert "Fonte Sentinel" not in content
    assert "Imagem Sentinel" not in content
    assert "Análise hidrológica Sentinel" not in content
    assert "Imagem Landsat" not in content
