"""Carrega o modelo treinado e faz predições sobre IoTPayload."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np

from ml.features import DETECTED_CLASSES, FEATURE_NAMES, extract_features

MODEL_DIR = Path(__file__).parent / "model"
MODEL_PATH = MODEL_DIR / "classifier.joblib"
METADATA_PATH = MODEL_DIR / "metadata.json"

_IMAGE_QUALITY_SCORE = {"boa": 0.9, "media": 0.6, "baixa": 0.3}

_RECOMMENDATIONS: dict[str, dict[str, str]] = {
    "queimada": {
        "alto": "Acionar resposta de campo para queimada e notificar autoridades ambientais.",
        "medio": "Validar foco com nova imagem e preparar equipe local.",
        "baixo": "Manter monitoramento preventivo da area.",
    },
    "solo_exposto": {
        "alto": "Priorizar vistoria para erosao, desmatamento ou obra irregular.",
        "medio": "Agendar revisita orbital e comparar historico recente.",
        "baixo": "Manter acompanhamento em ciclo regular.",
    },
    "agua": {
        "alto": "Verificar alteracao hidrica relevante com equipe responsavel.",
        "medio": "Monitorar nivel e checar eventos de cheia ou seca.",
        "baixo": "Manter monitoramento hidrico de rotina.",
    },
    "baixa_visibilidade": {
        "alto": "Reprocessar com novo frame antes de decisao operacional critica.",
        "medio": "Aguardar melhor visibilidade e repetir a analise.",
        "baixo": "Reagendar captura em ciclo regular.",
    },
    "vegetacao": {
        "alto": "Checar mudanca brusca de cobertura vegetal em campo.",
        "medio": "Comparar com serie historica e monitorar a area.",
        "baixo": "Manter monitoramento ambiental de rotina.",
    },
}


class ModelNotTrainedError(RuntimeError):
    """Lançado quando o modelo ainda não foi treinado."""


class _ModelCache:
    """Singleton que carrega o modelo uma única vez."""
    _clf = None
    _metadata: dict | None = None

    @classmethod
    def load(cls) -> tuple[Any, dict]:
        if cls._clf is None:
            if not MODEL_PATH.exists():
                raise ModelNotTrainedError(
                    f"Modelo não encontrado em {MODEL_PATH}. "
                    "Execute: python -m ml.train"
                )
            cls._clf = joblib.load(MODEL_PATH)
            cls._metadata = json.loads(METADATA_PATH.read_text())
        return cls._clf, cls._metadata  # type: ignore[return-value]

    @classmethod
    def clear(cls) -> None:
        cls._clf = None
        cls._metadata = None


def _build_explanation(data: dict, risk_level: str, clf: Any, features: np.ndarray) -> str:
    """Texto explicativo baseado nos top-2 features mais importantes do modelo."""
    importances: np.ndarray = clf.feature_importances_
    top2_idx = np.argsort(importances)[::-1][:2]

    parts = []
    for idx in top2_idx:
        name = FEATURE_NAMES[idx]
        value = float(features[idx])
        if name == "class_percentage":
            parts.append(f"cobertura {value * 100:.1f}%")
        elif name == "change_score":
            parts.append(f"mudanca {value:.2f}")
        elif name.startswith("class_"):
            if value > 0:
                parts.append(f"classe {name[6:]}")
        elif name == "image_quality_ord":
            label = {0.0: "baixa", 0.5: "media", 1.0: "boa"}.get(value, f"{value:.1f}")
            parts.append(f"qualidade {label}")
        else:
            parts.append(f"{name.replace('_', ' ')} {value:.2f}")

    detected = data["detected_class"].replace("_", " ")
    detail = ", ".join(parts) if parts else "multiplos fatores"
    return f"Risco {risk_level} detectado para {detected}: {detail}. Confianca CV {data['cv_confidence']:.2f}."


def predict(payload: Any) -> dict:
    """
    Recebe IoTPayload (ou dict) e retorna:
      risk_level, analysis_confidence, explanation, recommendation, model_version
    """
    clf, metadata = _ModelCache.load()

    if hasattr(payload, "model_dump"):
        data: dict = payload.model_dump()
    else:
        data = dict(payload)

    features = extract_features(data)
    features_2d = features.reshape(1, -1)

    risk_level: str = clf.predict(features_2d)[0]
    proba: np.ndarray = clf.predict_proba(features_2d)[0]
    max_proba = float(proba.max())

    iq_score = _IMAGE_QUALITY_SCORE[data["image_quality"]]
    cv_conf = float(data["cv_confidence"])
    analysis_confidence = round(
        max(0.0, min(1.0, max_proba * (iq_score * 0.45 + cv_conf * 0.55))),
        4,
    )

    explanation = _build_explanation(data, risk_level, clf, features)
    recommendation = _RECOMMENDATIONS[data["detected_class"]][risk_level]

    return {
        "risk_level": risk_level,
        "analysis_confidence": analysis_confidence,
        "explanation": explanation,
        "recommendation": recommendation,
        "model_version": metadata["model_version"],
    }
