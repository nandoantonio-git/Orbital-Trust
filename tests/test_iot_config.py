from iot.config import SUPPORTED_CLASSES, SUPPORTED_SOURCES


def test_supported_classes_not_empty():
    assert len(SUPPORTED_CLASSES) > 0
    assert all(isinstance(c, str) for c in SUPPORTED_CLASSES)


def test_supported_sources_contains_required():
    required = {"Sentinel-2", "Landsat", "FIRMS", "INPE"}
    assert required.issubset(set(SUPPORTED_SOURCES))
