from iot.stac_client import search_scenes


_MOCK_STAC_RESPONSE = {
    "type": "FeatureCollection",
    "features": [
        {
            "id": "S2A_MSIL2A_20240115",
            "type": "Feature",
            "properties": {
                "datetime": "2024-01-15T10:30:00Z",
                "eo:cloud_cover": 5.2,
            },
            "assets": {
                "B04": {"href": "https://example.com/B04.tif"},
                "B08": {"href": "https://example.com/B08.tif"},
            },
        },
        {
            "id": "S2B_MSIL2A_20240120",
            "type": "Feature",
            "properties": {
                "datetime": "2024-01-20T11:00:00Z",
                "eo:cloud_cover": 42.0,
            },
            "assets": {
                "B04": {"href": "https://example.com/B04b.tif"},
            },
        },
    ],
}


def test_search_scenes_returns_list():
    results = search_scenes(
        bbox=[-46.0, -23.0, -45.0, -22.0],
        start_date="2024-01-01",
        end_date="2024-01-31",
        source="Sentinel-2",
        max_cloud_score=30.0,
        _mock_response=_MOCK_STAC_RESPONSE,
    )
    assert isinstance(results, list)


def test_search_scenes_filters_by_cloud_score():
    results = search_scenes(
        bbox=[-46.0, -23.0, -45.0, -22.0],
        start_date="2024-01-01",
        end_date="2024-01-31",
        source="Sentinel-2",
        max_cloud_score=30.0,
        _mock_response=_MOCK_STAC_RESPONSE,
    )
    # The second item has cloud_score=42.0, should be filtered out
    assert len(results) == 1
    assert results[0]["scene_id"] == "S2A_MSIL2A_20240115"


def test_search_scenes_normalized_fields():
    results = search_scenes(
        bbox=[-46.0, -23.0, -45.0, -22.0],
        start_date="2024-01-01",
        end_date="2024-01-31",
        source="Sentinel-2",
        max_cloud_score=100.0,
        _mock_response=_MOCK_STAC_RESPONSE,
    )
    assert len(results) == 2
    scene = results[0]
    assert "scene_id" in scene
    assert "source" in scene
    assert "datetime" in scene
    assert "cloud_score" in scene
    assert "assets" in scene


def test_search_scenes_source_field_matches_input():
    results = search_scenes(
        bbox=[-46.0, -23.0, -45.0, -22.0],
        start_date="2024-01-01",
        end_date="2024-01-31",
        source="Landsat",
        max_cloud_score=100.0,
        _mock_response=_MOCK_STAC_RESPONSE,
    )
    for scene in results:
        assert scene["source"] == "Landsat"


def test_search_scenes_assets_are_strings():
    results = search_scenes(
        bbox=[-46.0, -23.0, -45.0, -22.0],
        start_date="2024-01-01",
        end_date="2024-01-31",
        source="Sentinel-2",
        max_cloud_score=100.0,
        _mock_response=_MOCK_STAC_RESPONSE,
    )
    for scene in results:
        assert isinstance(scene["assets"], dict)
        for href in scene["assets"].values():
            assert isinstance(href, str)


def test_search_scenes_empty_mock():
    results = search_scenes(
        bbox=[-46.0, -23.0, -45.0, -22.0],
        start_date="2024-01-01",
        end_date="2024-01-31",
        source="INPE",
        max_cloud_score=30.0,
        _mock_response={"type": "FeatureCollection", "features": []},
    )
    assert results == []
