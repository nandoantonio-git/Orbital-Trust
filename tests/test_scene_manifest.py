import json
import os
import pytest

from iot.scene_manifest import build_scene_manifest, MANIFESTS_DIR


_SCENE_WITH_VISUAL = {
    "scene_id": "S2A_20240115",
    "source": "Sentinel-2",
    "datetime": "2024-01-15T10:30:00Z",
    "cloud_score": 5.2,
    "assets": {
        "B04": "https://example.com/B04.tif",
        "thumbnail": "https://example.com/thumb.jpg",
        "B08": "https://example.com/B08.tif",
    },
}

_SCENE_WITHOUT_VISUAL = {
    "scene_id": "LC08_20240120",
    "source": "Landsat",
    "datetime": "2024-01-20T12:00:00Z",
    "cloud_score": 12.0,
    "assets": {
        "B5": "https://example.com/B5.tif",
        "B4": "https://example.com/B4.tif",
    },
}

_SCENE_NO_ASSETS = {
    "scene_id": "INPE_20240125",
    "source": "INPE",
    "datetime": "2024-01-25T08:00:00Z",
    "cloud_score": 0.0,
    "assets": {},
}


def test_manifest_required_fields():
    manifest = build_scene_manifest([_SCENE_WITH_VISUAL], area_id="area-001")
    assert manifest["area_id"] == "area-001"
    assert "generated_at" in manifest
    assert "scenes" in manifest


def test_manifest_scene_fields():
    manifest = build_scene_manifest([_SCENE_WITH_VISUAL], area_id="area-001")
    entry = manifest["scenes"][0]
    assert entry["area_id"] == "area-001"
    assert entry["source"] == "Sentinel-2"
    assert entry["scene_id"] == "S2A_20240115"
    assert entry["datetime"] == "2024-01-15T10:30:00Z"
    assert entry["cloud_score"] == 5.2
    assert "asset_href" in entry


def test_selects_thumbnail_asset():
    manifest = build_scene_manifest([_SCENE_WITH_VISUAL], area_id="area-002")
    entry = manifest["scenes"][0]
    assert entry["asset_href"] == "https://example.com/thumb.jpg"


def test_fallback_asset_when_no_visual():
    manifest = build_scene_manifest([_SCENE_WITHOUT_VISUAL], area_id="area-003")
    entry = manifest["scenes"][0]
    assert entry["asset_href"] != ""


def test_empty_asset_href_when_no_assets():
    manifest = build_scene_manifest([_SCENE_NO_ASSETS], area_id="area-004")
    entry = manifest["scenes"][0]
    assert entry["asset_href"] == ""


def test_saves_manifest_to_disk(tmp_path, monkeypatch):
    monkeypatch.setattr("iot.scene_manifest.MANIFESTS_DIR", str(tmp_path))
    build_scene_manifest([_SCENE_WITH_VISUAL], area_id="area-save")
    saved = tmp_path / "area-save.json"
    assert saved.exists()
    data = json.loads(saved.read_text())
    assert data["area_id"] == "area-save"
    assert len(data["scenes"]) == 1


def test_multiple_scenes():
    manifest = build_scene_manifest(
        [_SCENE_WITH_VISUAL, _SCENE_WITHOUT_VISUAL], area_id="area-multi"
    )
    assert len(manifest["scenes"]) == 2
