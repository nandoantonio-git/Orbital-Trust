from iot.config import SUPPORTED_CLASSES, SUPPORTED_SOURCES
from iot.detector import detect_class


def _solid_bgr(b: int, g: int, r: int):
    import numpy as np

    frame = np.zeros((20, 20, 3), dtype=np.uint8)
    frame[:, :] = (b, g, r)
    return frame


def test_supported_classes_match_contract():
    assert SUPPORTED_CLASSES == [
        "vegetacao",
        "solo_exposto",
        "agua",
        "queimada",
        "baixa_visibilidade",
    ]


def test_supported_sources_match_contract():
    assert SUPPORTED_SOURCES == ["Sentinel-2", "Landsat", "FIRMS", "INPE"]


def test_supported_classes_cover_detect_class_outputs():
    frames = [
        _solid_bgr(0, 200, 0),
        _solid_bgr(80, 100, 130),
        _solid_bgr(200, 0, 0),
        _solid_bgr(20, 20, 20),
        _solid_bgr(200, 200, 200),
    ]

    detected_classes = {detect_class(frame)["detected_class"] for frame in frames}

    assert detected_classes == set(SUPPORTED_CLASSES)
