import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from api.main import AlertResponse, app, derive_risk_level


client = TestClient(app)


def _payload(**overrides):
    payload = {
        "event_id": "EVT-2024-09-30-001",
        "timestamp": "2024-09-30T12:00:00Z",
        "area_id": "BR-MT-001",
        "source": "Sentinel-2",
        "detected_class": "vegetacao",
        "class_percentage": 42.7,
        "change_score": 0.1,
        "cloud_score": 0.04,
        "shadow_score": 0.12,
        "image_quality": 0.91,
        "cv_confidence": 0.87,
    }
    payload.update(overrides)
    return payload


def test_analyze_alert_returns_low_risk():
    response = client.post("/alerts/analyze", json=_payload())

    assert response.status_code == 200
    data = response.json()
    assert data["event_id"] == "EVT-2024-09-30-001"
    assert data["risk_level"] == "baixo"
    assert data["analysis_confidence"] == 0.888
    assert data["model_version"] == "orbital-heuristic-v0.1.0"


def test_analyze_alert_returns_medium_risk():
    response = client.post(
        "/alerts/analyze",
        json=_payload(change_score=0.35, detected_class="agua", image_quality=0.8),
    )

    assert response.status_code == 200
    assert response.json()["risk_level"] == "medio"


def test_analyze_alert_returns_high_risk():
    response = client.post(
        "/alerts/analyze",
        json=_payload(change_score=0.5, detected_class="queimada", cv_confidence=0.78),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["risk_level"] == "alto"
    assert "queimada" in data["recommendation"].lower()


def test_analyze_alert_rejects_incomplete_iot_payload():
    payload = _payload()
    del payload["change_score"]

    response = client.post("/alerts/analyze", json=payload)

    assert response.status_code == 422


def test_analyze_alert_rejects_invalid_source():
    response = client.post("/alerts/analyze", json=_payload(source="MODIS/GIBS"))

    assert response.status_code == 422


def test_alert_response_rejects_invalid_risk_level():
    with pytest.raises(ValidationError):
        AlertResponse(
            event_id="EVT-1",
            timestamp="2024-09-30T12:00:00Z",
            detected_class="vegetacao",
            risk_level="critico",
            analysis_confidence=0.9,
            explanation="x",
            recommendation="y",
            model_version="orbital-heuristic-v0.1.0",
        )


def test_heuristic_uses_quality_and_confidence():
    assert (
        derive_risk_level(
            change_score=0.24,
            detected_class="vegetacao",
            image_quality=0.2,
            cv_confidence=0.2,
        )
        == "medio"
    )
