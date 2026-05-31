import numpy as np
import pytest

from iot.detector import detect_class


def _solid_bgr(b: int, g: int, r: int, size: int = 100) -> np.ndarray:
    frame = np.zeros((size, size, 3), dtype=np.uint8)
    frame[:, :] = (b, g, r)
    return frame


def test_detect_vegetacao():
    # BGR(0,200,0) — G dominant, pure green
    result = detect_class(_solid_bgr(0, 200, 0))
    assert result["detected_class"] == "vegetacao"
    assert result["class_percentage"] >= 90.0


def test_detect_agua():
    # BGR(200,0,0) — B dominant, pure blue
    result = detect_class(_solid_bgr(200, 0, 0))
    assert result["detected_class"] == "agua"
    assert result["class_percentage"] >= 90.0


def test_detect_queimada():
    # BGR(20,20,20) — very dark, mean < 40
    result = detect_class(_solid_bgr(20, 20, 20))
    assert result["detected_class"] == "queimada"
    assert result["class_percentage"] >= 90.0


def test_detect_solo_exposto():
    # BGR(30,100,160) — R dominant
    result = detect_class(_solid_bgr(30, 100, 160))
    assert result["detected_class"] == "solo_exposto"
    assert result["class_percentage"] >= 90.0


def test_return_schema():
    result = detect_class(_solid_bgr(0, 200, 0))
    assert "detected_class" in result
    assert "class_percentage" in result
    assert isinstance(result["detected_class"], str)
    assert isinstance(result["class_percentage"], float)
    assert 0.0 <= result["class_percentage"] <= 100.0


# Story US-041: BGR channel dominance — explicit AC test cases
def test_detect_agua_bgr_150_100_50():
    # AC: frame azul (150,100,50 BGR) → agua
    result = detect_class(_solid_bgr(150, 100, 50))
    assert result["detected_class"] == "agua"
    assert result["class_percentage"] >= 90.0


def test_detect_vegetacao_bgr_50_150_50():
    # AC: frame verde (50,150,50 BGR) → vegetacao
    result = detect_class(_solid_bgr(50, 150, 50))
    assert result["detected_class"] == "vegetacao"
    assert result["class_percentage"] >= 90.0


def test_detect_queimada_bgr_20_20_20():
    # AC: frame escuro (20,20,20 BGR) → queimada
    result = detect_class(_solid_bgr(20, 20, 20))
    assert result["detected_class"] == "queimada"
    assert result["class_percentage"] >= 90.0


def test_detect_baixa_visibilidade_bgr_200_200_200():
    # AC: frame branco-acinzentado (200,200,200 BGR) → baixa_visibilidade
    result = detect_class(_solid_bgr(200, 200, 200))
    assert result["detected_class"] == "baixa_visibilidade"
    assert result["class_percentage"] >= 90.0


def test_detect_solo_exposto_bgr_80_100_130():
    # AC: frame marrom (80,100,130 BGR) → solo_exposto
    result = detect_class(_solid_bgr(80, 100, 130))
    assert result["detected_class"] == "solo_exposto"
    assert result["class_percentage"] >= 90.0


def test_detect_class_rejects_empty_array():
    with pytest.raises(ValueError):
        detect_class(np.array([], dtype=np.uint8))


def test_detect_class_rejects_grayscale_frame():
    frame = np.zeros((10, 10), dtype=np.uint8)

    with pytest.raises(ValueError):
        detect_class(frame)


def test_detect_class_rejects_non_numeric_frame():
    frame = np.full((10, 10, 3), "x", dtype=object)

    with pytest.raises(ValueError):
        detect_class(frame)
