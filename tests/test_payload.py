import pytest
from iot.payload import build_payload


_DETECTOR = {"detected_class": "vegetacao", "class_percentage": 0.72}
_QUALITY = {"cloud_score": 0.05, "shadow_score": 0.02, "image_quality": 0.95, "cv_confidence": 0.88}


def test_build_payload_returns_all_fields():
    payload = build_payload(
        event_id="evt-001",
        area_id="area-br-001",
        source="Sentinel-2",
        detector_result=_DETECTOR,
        quality_result=_QUALITY,
        change_score=0.3,
        frame_reference="frames/s2_20240501.tif",
    )
    required = (
        "event_id", "timestamp", "area_id", "source",
        "detected_class", "class_percentage", "change_score",
        "cloud_score", "shadow_score", "image_quality",
        "cv_confidence", "frame_reference",
    )
    for field in required:
        assert field in payload, f"Campo ausente: {field}"


def test_build_payload_values_are_correct():
    payload = build_payload(
        event_id="evt-002",
        area_id="area-br-002",
        source="Landsat",
        detector_result=_DETECTOR,
        quality_result=_QUALITY,
        change_score=0.55,
        frame_reference="frames/l8_20240502.tif",
    )
    assert payload["event_id"] == "evt-002"
    assert payload["area_id"] == "area-br-002"
    assert payload["source"] == "Landsat"
    assert payload["detected_class"] == "vegetacao"
    assert payload["class_percentage"] == 0.72
    assert payload["change_score"] == 0.55
    assert payload["cloud_score"] == 0.05
    assert payload["shadow_score"] == 0.02
    assert payload["image_quality"] == 0.95
    assert payload["cv_confidence"] == 0.88
    assert payload["frame_reference"] == "frames/l8_20240502.tif"
    assert "timestamp" in payload


def test_build_payload_missing_event_id_raises():
    with pytest.raises((ValueError, KeyError)):
        build_payload(
            event_id="",
            area_id="area-br-001",
            source="Sentinel-2",
            detector_result=_DETECTOR,
            quality_result=_QUALITY,
            change_score=0.1,
            frame_reference="frames/x.tif",
        )


def test_build_payload_missing_detector_field_raises():
    with pytest.raises(KeyError):
        build_payload(
            event_id="evt-003",
            area_id="area-br-001",
            source="Sentinel-2",
            detector_result={},  # missing detected_class and class_percentage
            quality_result=_QUALITY,
            change_score=0.1,
            frame_reference="frames/x.tif",
        )


def test_build_payload_missing_quality_field_raises():
    with pytest.raises(KeyError):
        build_payload(
            event_id="evt-004",
            area_id="area-br-001",
            source="Sentinel-2",
            detector_result=_DETECTOR,
            quality_result={},  # missing cloud_score etc.
            change_score=0.1,
            frame_reference="frames/x.tif",
        )
