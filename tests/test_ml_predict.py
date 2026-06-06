"""Testes unitários para ml/features.py e ml/predict.py."""

import pytest
import numpy as np

from ml.features import FEATURE_NAMES, extract_features
from ml.predict import ModelNotTrainedError, _ModelCache, predict

_BASE_PAYLOAD = {
    "event_id": "e1",
    "timestamp": "2024-01-01T00:00:00Z",
    "area_id": "BR-MT-001",
    "source": "Sentinel-2",
    "detected_class": "queimada",
    "class_percentage": 72.0,
    "change_score": 0.85,
    "cloud_score": 0.10,
    "shadow_score": 0.05,
    "brightness_score": 0.60,
    "blur_score": 0.20,
    "image_quality": "boa",
    "cv_confidence": 0.91,
    "frame_reference": "frame_mt_20240601.jpg",
    "algorithm_version": "orbital-cv-v0.2.0",
}


# ---------------------------------------------------------------------------
# features.py
# ---------------------------------------------------------------------------

def test_extract_features_shape():
    # 8 numeric + 5 detected_class one-hot + 4 source one-hot = 17
    features = extract_features(_BASE_PAYLOAD)
    assert features.shape == (17,), f"Esperado (17,), obtido {features.shape}"


def test_extract_features_names_count():
    assert len(FEATURE_NAMES) == 17


def test_extract_features_range():
    features = extract_features(_BASE_PAYLOAD)
    assert np.all(features >= 0.0), "Todas as features devem ser >= 0"
    assert np.all(features <= 1.0), "Todas as features devem ser <= 1"


def test_extract_features_class_percentage_normalized():
    payload = {**_BASE_PAYLOAD, "class_percentage": 50.0}
    features = extract_features(payload)
    assert abs(features[0] - 0.5) < 1e-6


def test_extract_features_one_hot_detected_class():
    for cls in ["vegetacao", "solo_exposto", "agua", "queimada", "baixa_visibilidade"]:
        payload = {**_BASE_PAYLOAD, "detected_class": cls}
        features = extract_features(payload)
        # Os índices 8-12 são o one-hot de detected_class
        onehot = features[8:13]
        assert onehot.sum() == 1.0, f"One-hot deve ter exatamente um 1 para {cls}"


def test_extract_features_image_quality_ordinal():
    for iq, expected in [("baixa", 0.0), ("media", 0.5), ("boa", 1.0)]:
        payload = {**_BASE_PAYLOAD, "image_quality": iq}
        features = extract_features(payload)
        assert abs(features[7] - expected) < 1e-6, f"image_quality {iq} → {features[7]}"


# ---------------------------------------------------------------------------
# predict.py — sem modelo treinado
# ---------------------------------------------------------------------------

def test_predict_raises_model_not_trained_error(tmp_path, monkeypatch):
    import ml.predict as mp
    monkeypatch.setattr(mp, "MODEL_PATH", tmp_path / "nao_existe.joblib")
    _ModelCache.clear()
    with pytest.raises(ModelNotTrainedError):
        predict(_BASE_PAYLOAD)
    _ModelCache.clear()


# ---------------------------------------------------------------------------
# predict.py — com modelo treinado
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def trained_model():
    """Treina o modelo uma vez para os testes de predict."""
    from ml.train import train_and_save
    train_and_save()
    _ModelCache.clear()
    yield
    _ModelCache.clear()


def test_predict_returns_required_keys(trained_model):
    result = predict(_BASE_PAYLOAD)
    for key in ("risk_level", "analysis_confidence", "explanation", "recommendation", "model_version"):
        assert key in result, f"Chave '{key}' ausente no resultado"


def test_predict_risk_level_valid(trained_model):
    result = predict(_BASE_PAYLOAD)
    assert result["risk_level"] in ("baixo", "medio", "alto")


def test_predict_analysis_confidence_range(trained_model):
    result = predict(_BASE_PAYLOAD)
    conf = result["analysis_confidence"]
    assert 0.0 <= conf <= 1.0, f"analysis_confidence fora do range: {conf}"


def test_predict_model_version_format(trained_model):
    result = predict(_BASE_PAYLOAD)
    assert result["model_version"].startswith("orbital-ml-")


def test_predict_all_classes(trained_model):
    for cls in ["vegetacao", "solo_exposto", "agua", "queimada", "baixa_visibilidade"]:
        payload = {**_BASE_PAYLOAD, "detected_class": cls}
        result = predict(payload)
        assert result["risk_level"] in ("baixo", "medio", "alto")


def test_predict_queimada_high_change_is_alto(trained_model):
    payload = {
        **_BASE_PAYLOAD,
        "detected_class": "queimada",
        "change_score": 0.95,
        "image_quality": "boa",
        "cv_confidence": 0.95,
    }
    result = predict(payload)
    assert result["risk_level"] == "alto", (
        f"queimada com change_score 0.95 deveria ser 'alto', obteve '{result['risk_level']}'"
    )


def test_predict_vegetacao_low_change_is_baixo(trained_model):
    payload = {
        **_BASE_PAYLOAD,
        "detected_class": "vegetacao",
        "change_score": 0.05,
        "image_quality": "boa",
        "cv_confidence": 0.90,
    }
    result = predict(payload)
    assert result["risk_level"] == "baixo", (
        f"vegetacao com change_score 0.05 deveria ser 'baixo', obteve '{result['risk_level']}'"
    )
