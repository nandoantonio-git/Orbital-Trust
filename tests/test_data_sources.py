from iot.data_sources import INPE_BDC_STAC_URL, COPERNICUS_STAC_URL, SUPPORTED_SOURCES


def test_inpe_bdc_stac_url_defined():
    assert isinstance(INPE_BDC_STAC_URL, str)
    assert INPE_BDC_STAC_URL.startswith("https://")


def test_copernicus_stac_url_defined():
    assert isinstance(COPERNICUS_STAC_URL, str)
    assert COPERNICUS_STAC_URL.startswith("https://")


def test_supported_sources_contains_required():
    assert SUPPORTED_SOURCES == ["Sentinel-2", "Landsat", "FIRMS", "INPE"]


def test_supported_sources_not_empty():
    assert len(SUPPORTED_SOURCES) > 0
    assert all(isinstance(s, str) for s in SUPPORTED_SOURCES)
