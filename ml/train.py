"""Gera dados sintéticos, treina RandomForestClassifier e salva em ml/model/."""

from __future__ import annotations

import json
import os
import random
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score

from ml.features import DETECTED_CLASSES, IMAGE_QUALITY_ORDINAL, SOURCES, extract_features

MODEL_DIR = Path(__file__).parent / "model"
MODEL_PATH = MODEL_DIR / "classifier.joblib"
METADATA_PATH = MODEL_DIR / "metadata.json"

MODEL_VERSION = "orbital-ml-v1.0.0"
N_SAMPLES = 1200
RISK_LEVELS = ["baixo", "medio", "alto"]
MIN_CV_ACCURACY = 0.90


# ---------------------------------------------------------------------------
# Heurística de bootstrap (espelho de api/main.py:derive_risk_level)
# ---------------------------------------------------------------------------

def _image_quality_score(iq: str) -> float:
    return {"boa": 0.9, "media": 0.6, "baixa": 0.3}[iq]


def _heuristic_label(sample: dict) -> str:
    class_weight = {
        "queimada": 0.25,
        "solo_exposto": 0.12,
        "baixa_visibilidade": 0.10,
        "agua": 0.06,
        "vegetacao": 0.0,
    }[sample["detected_class"]]
    quality_penalty = max(0.0, 0.70 - _image_quality_score(sample["image_quality"])) * 0.20
    confidence_penalty = max(0.0, 0.70 - sample["cv_confidence"]) * 0.15
    score = sample["change_score"] + class_weight + quality_penalty + confidence_penalty
    if score > 0.50:
        return "alto"
    if score > 0.20:
        return "medio"
    return "baixo"


# ---------------------------------------------------------------------------
# Geração de amostras sintéticas
# ---------------------------------------------------------------------------

def _generate_samples(n: int, seed: int = 42) -> tuple[np.ndarray, list[str]]:
    rng = random.Random(seed)
    np.random.seed(seed)

    X_rows: list[np.ndarray] = []
    y_labels: list[str] = []

    # Distribuição alvo: 25% baixo, 45% medio, 30% alto
    # Geração guiada para cobrir cada nível de risco proporcionalmente
    target_counts = {"baixo": int(n * 0.25), "alto": int(n * 0.30)}
    target_counts["medio"] = n - target_counts["baixo"] - target_counts["alto"]
    counters = {"baixo": 0, "medio": 0, "alto": 0}

    attempts = 0
    while sum(counters.values()) < n and attempts < n * 20:
        attempts += 1

        detected_class = rng.choice(DETECTED_CLASSES)
        source = rng.choice(SOURCES)
        image_quality = rng.choice(list(IMAGE_QUALITY_ORDINAL.keys()))
        class_percentage = rng.uniform(0.0, 100.0)
        change_score = rng.uniform(0.0, 1.0)
        cloud_score = rng.uniform(0.0, 1.0)
        shadow_score = rng.uniform(0.0, 1.0)
        brightness_score = rng.uniform(0.0, 1.0)
        blur_score = rng.uniform(0.0, 1.0)
        cv_confidence = rng.uniform(0.0, 1.0)

        sample = {
            "detected_class": detected_class,
            "source": source,
            "image_quality": image_quality,
            "class_percentage": class_percentage,
            "change_score": change_score,
            "cloud_score": cloud_score,
            "shadow_score": shadow_score,
            "brightness_score": brightness_score,
            "blur_score": blur_score,
            "cv_confidence": cv_confidence,
        }

        label = _heuristic_label(sample)

        # Aceita se ainda precisamos de amostras desse nível
        if counters[label] < target_counts[label]:
            counters[label] += 1
            X_rows.append(extract_features(sample))
            y_labels.append(label)

    # Completar com amostras aleatórias sem restrição de proporção
    while len(X_rows) < n:
        detected_class = rng.choice(DETECTED_CLASSES)
        source = rng.choice(SOURCES)
        image_quality = rng.choice(list(IMAGE_QUALITY_ORDINAL.keys()))
        sample = {
            "detected_class": detected_class,
            "source": source,
            "image_quality": image_quality,
            "class_percentage": rng.uniform(0.0, 100.0),
            "change_score": rng.uniform(0.0, 1.0),
            "cloud_score": rng.uniform(0.0, 1.0),
            "shadow_score": rng.uniform(0.0, 1.0),
            "brightness_score": rng.uniform(0.0, 1.0),
            "blur_score": rng.uniform(0.0, 1.0),
            "cv_confidence": rng.uniform(0.0, 1.0),
        }
        X_rows.append(extract_features(sample))
        y_labels.append(_heuristic_label(sample))

    return np.array(X_rows), y_labels


# ---------------------------------------------------------------------------
# Treinamento
# ---------------------------------------------------------------------------

def train_and_save() -> None:
    print(f"Gerando {N_SAMPLES} amostras sintéticas...")
    X, y = _generate_samples(N_SAMPLES)

    clf = RandomForestClassifier(
        n_estimators=100,
        class_weight="balanced",
        random_state=42,
    )

    print("Avaliando com cross-validation 5-fold...")
    cv_scores = cross_val_score(clf, X, y, cv=5, scoring="accuracy")
    cv_mean = float(cv_scores.mean())
    cv_std = float(cv_scores.std())
    print(f"CV accuracy: {cv_mean:.4f} ± {cv_std:.4f}")

    if cv_mean < MIN_CV_ACCURACY:
        raise RuntimeError(
            f"Acurácia {cv_mean:.4f} abaixo do mínimo exigido ({MIN_CV_ACCURACY}). "
            "Modelo NÃO salvo."
        )

    clf.fit(X, y)

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(clf, MODEL_PATH)

    from ml.features import FEATURE_NAMES
    metadata = {
        "model_version": MODEL_VERSION,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "cv_accuracy_mean": round(cv_mean, 6),
        "cv_accuracy_std": round(cv_std, 6),
        "n_samples": N_SAMPLES,
        "features": FEATURE_NAMES,
    }
    METADATA_PATH.write_text(json.dumps(metadata, indent=2, ensure_ascii=False))

    print(f"Modelo salvo em {MODEL_PATH}")
    print(f"Metadados salvos em {METADATA_PATH}")


if __name__ == "__main__":
    train_and_save()
