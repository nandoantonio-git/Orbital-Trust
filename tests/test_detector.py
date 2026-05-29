import numpy as np
from iot.detector import detect_class


def _solid_bgr(b: int, g: int, r: int, size: int = 100) -> np.ndarray:
    frame = np.zeros((size, size, 3), dtype=np.uint8)
    frame[:, :] = (b, g, r)
    return frame


def test_detect_vegetacao():
    # BGR(0,200,0) → HSV H=60, S=255, V=200 — pure green
    result = detect_class(_solid_bgr(0, 200, 0))
    assert result["detected_class"] == "vegetacao"
    assert result["class_percentage"] >= 0.9


def test_detect_agua():
    # BGR(200,0,0) → HSV H=120, S=255, V=200 — pure blue
    result = detect_class(_solid_bgr(200, 0, 0))
    assert result["detected_class"] == "agua"
    assert result["class_percentage"] >= 0.9


def test_detect_queimada():
    # BGR(20,20,20) → HSV V=20 — very dark
    result = detect_class(_solid_bgr(20, 20, 20))
    assert result["detected_class"] == "queimada"
    assert result["class_percentage"] >= 0.9


def test_detect_baixa_visibilidade():
    # BGR(200,200,200) → HSV S=0, V=200 — gray/cloud
    result = detect_class(_solid_bgr(200, 200, 200))
    assert result["detected_class"] == "baixa_visibilidade"
    assert result["class_percentage"] >= 0.9


def test_detect_solo_exposto():
    # BGR(30,100,160) → HSV H≈16, S≈207, V=160 — brown/tan
    result = detect_class(_solid_bgr(30, 100, 160))
    assert result["detected_class"] == "solo_exposto"
    assert result["class_percentage"] >= 0.9


def test_return_schema():
    result = detect_class(_solid_bgr(0, 200, 0))
    assert "detected_class" in result
    assert "class_percentage" in result
    assert isinstance(result["detected_class"], str)
    assert isinstance(result["class_percentage"], float)
    assert 0.0 <= result["class_percentage"] <= 1.0
