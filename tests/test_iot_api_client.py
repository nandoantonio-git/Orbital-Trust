import json

from iot.api_client import post_payload_to_api


def _payload(**overrides):
    payload = {
        "event_id": "EVT-API-001",
        "timestamp": "2024-09-30T12:00:00+00:00",
        "area_id": "BR-MT-001",
        "source": "Sentinel-2",
        "detected_class": "queimada",
        "class_percentage": 42.0,
        "change_score": 0.7,
        "cloud_score": 0.1,
        "shadow_score": 0.05,
        "brightness_score": 0.6,
        "blur_score": 0.2,
        "image_quality": "boa",
        "cv_confidence": 0.86,
        "frame_reference": "frame_a.jpg>frame_b.jpg",
        "algorithm_version": "orbital-cv-v0.2.0",
        "tile_quality": {"black_ratio": 0.0},
    }
    payload.update(overrides)
    return payload


class _Response:
    def __init__(self, ok=True, status_code=200, text=""):
        self.ok = ok
        self.status_code = status_code
        self.text = text

    def json(self):
        return {
            "event_id": "EVT-API-001",
            "risk_level": "alto",
            "analysis_confidence": 0.91,
            "explanation": "risco alto",
            "recommendation": "verificar area",
            "model_version": "api-v0.1.0",
        }


def test_post_payload_to_api_success_posts_once_without_fallback(tmp_path):
    calls = []

    def fake_post(endpoint, json, timeout):
        calls.append((endpoint, json, timeout))
        return _Response(ok=True)

    result = post_payload_to_api(
        "http://localhost:8000/",
        _payload(),
        timeout=1.5,
        fallback_dir=tmp_path,
        post=fake_post,
    )

    assert result["risk_level"] == "alto"
    assert len(calls) == 1
    assert calls[0][0] == "http://localhost:8000/alerts/analyze"
    assert calls[0][2] == 1.5
    assert "tile_quality" not in calls[0][1]
    assert list(tmp_path.glob("*.json")) == []


def test_post_payload_connection_error_logs_and_saves_fallback(tmp_path, capsys):
    calls = []

    def fake_post(endpoint, json, timeout):
        calls.append(endpoint)
        raise ConnectionError("api offline")

    result = post_payload_to_api(
        "http://api.local",
        _payload(),
        fallback_dir=tmp_path,
        post=fake_post,
    )

    assert result is None
    assert calls == ["http://api.local/alerts/analyze"]

    captured = capsys.readouterr()
    assert "status=connection_error" in captured.err
    assert "endpoint=http://api.local/alerts/analyze" in captured.err
    assert "event_id=EVT-API-001" in captured.err

    fallback_files = list(tmp_path.glob("*.json"))
    assert len(fallback_files) == 1
    saved = json.loads(fallback_files[0].read_text(encoding="utf-8"))
    assert saved["event_id"] == "EVT-API-001"
    assert "tile_quality" not in saved


def test_post_payload_timeout_logs_status_and_saves_fallback(tmp_path, capsys):
    def fake_post(endpoint, json, timeout):
        raise TimeoutError("request timed out")

    result = post_payload_to_api(
        "http://api.local",
        _payload(),
        fallback_dir=tmp_path,
        post=fake_post,
    )

    assert result is None
    assert "status=timeout" in capsys.readouterr().err
    assert len(list(tmp_path.glob("*.json"))) == 1


def test_post_payload_http_error_logs_status_and_saves_fallback(tmp_path, capsys):
    calls = 0

    def fake_post(endpoint, json, timeout):
        nonlocal calls
        calls += 1
        return _Response(ok=False, status_code=503, text="service unavailable")

    result = post_payload_to_api(
        "http://api.local",
        _payload(),
        fallback_dir=tmp_path,
        post=fake_post,
    )

    assert result is None
    assert calls == 1
    captured = capsys.readouterr()
    assert "status=http_503" in captured.err
    assert "endpoint=http://api.local/alerts/analyze" in captured.err
    assert "event_id=EVT-API-001" in captured.err
    assert len(list(tmp_path.glob("*.json"))) == 1


def test_post_payload_invalid_json_response_does_not_raise(tmp_path, capsys):
    class InvalidJsonResponse(_Response):
        def json(self):
            raise ValueError("invalid json")

    result = post_payload_to_api(
        "http://api.local",
        _payload(),
        fallback_dir=tmp_path,
        post=lambda endpoint, json, timeout: InvalidJsonResponse(ok=True),
    )

    assert result is None
    assert "status=invalid_response" in capsys.readouterr().err
    assert len(list(tmp_path.glob("*.json"))) == 1
