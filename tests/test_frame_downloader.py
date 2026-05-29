import json
import os
from unittest.mock import patch, call

import pytest

from iot.frame_downloader import download_scene_frames, _traceable_filename


_MANIFEST = {
    "area_id": "area-001",
    "generated_at": "2026-01-01T00:00:00Z",
    "scenes": [
        {
            "area_id": "area-001",
            "source": "Sentinel-2",
            "scene_id": "S2A_20240115",
            "datetime": "2024-01-15T10:30:00Z",
            "cloud_score": 5.2,
            "asset_href": "https://example.com/thumb.jpg",
        },
        {
            "area_id": "area-001",
            "source": "Landsat",
            "scene_id": "LC08_20240120",
            "datetime": "2024-01-20T12:00:00Z",
            "cloud_score": 12.0,
            "asset_href": "https://example.com/lc08.png",
        },
    ],
}


def _write_manifest(tmp_path, data=None):
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data or _MANIFEST))
    return str(p)


def test_returns_list_of_paths(tmp_path):
    manifest_path = _write_manifest(tmp_path)
    output_folder = str(tmp_path / "frames")

    with patch("urllib.request.urlretrieve") as mock_dl:
        def fake_download(url, dest):
            open(dest, "wb").close()
        mock_dl.side_effect = fake_download

        result = download_scene_frames(manifest_path, output_folder)

    assert isinstance(result, list)
    assert len(result) == 2


def test_filenames_contain_source_area_scene(tmp_path):
    manifest_path = _write_manifest(tmp_path)
    output_folder = str(tmp_path / "frames")

    with patch("urllib.request.urlretrieve") as mock_dl:
        def fake_download(url, dest):
            open(dest, "wb").close()
        mock_dl.side_effect = fake_download

        result = download_scene_frames(manifest_path, output_folder)

    names = [os.path.basename(p) for p in result]
    assert any("sentinel-2" in n and "area-001" in n and "s2a_20240115" in n for n in names)
    assert any("landsat" in n and "area-001" in n and "lc08_20240120" in n for n in names)


def test_creates_output_folder(tmp_path):
    manifest_path = _write_manifest(tmp_path)
    output_folder = str(tmp_path / "nested" / "frames")

    with patch("urllib.request.urlretrieve") as mock_dl:
        def fake_download(url, dest):
            open(dest, "wb").close()
        mock_dl.side_effect = fake_download

        download_scene_frames(manifest_path, output_folder)

    assert os.path.isdir(output_folder)


def test_skips_existing_files(tmp_path):
    manifest_path = _write_manifest(tmp_path)
    output_folder = str(tmp_path / "frames")
    os.makedirs(output_folder)

    # Pre-create one file
    existing_name = _traceable_filename("Sentinel-2", "area-001", "S2A_20240115", "https://example.com/thumb.jpg")
    existing_path = os.path.join(output_folder, existing_name)
    open(existing_path, "wb").close()

    with patch("urllib.request.urlretrieve") as mock_dl:
        def fake_download(url, dest):
            open(dest, "wb").close()
        mock_dl.side_effect = fake_download

        result = download_scene_frames(manifest_path, output_folder)

    # urlretrieve called only once (for the second scene)
    assert mock_dl.call_count == 1
    assert existing_path in result


def test_failure_does_not_break_other_downloads(tmp_path):
    manifest_path = _write_manifest(tmp_path)
    output_folder = str(tmp_path / "frames")

    import urllib.error

    call_count = [0]

    def fake_download(url, dest):
        call_count[0] += 1
        if call_count[0] == 1:
            raise urllib.error.URLError("connection refused")
        open(dest, "wb").close()

    with patch("urllib.request.urlretrieve", side_effect=fake_download):
        result = download_scene_frames(manifest_path, output_folder)

    # Second scene still downloaded despite first failing
    assert len(result) == 1


def test_scene_with_empty_href_is_skipped(tmp_path):
    manifest = {
        "area_id": "area-x",
        "scenes": [
            {"area_id": "area-x", "source": "INPE", "scene_id": "X001", "asset_href": ""},
        ],
    }
    manifest_path = _write_manifest(tmp_path, manifest)
    output_folder = str(tmp_path / "frames")

    with patch("urllib.request.urlretrieve") as mock_dl:
        result = download_scene_frames(manifest_path, output_folder)

    assert result == []
    mock_dl.assert_not_called()


def test_traceable_filename_format():
    name = _traceable_filename("Sentinel-2", "area-001", "S2A_20240115", "https://x.com/img.jpg")
    assert name == "sentinel-2__area-001__s2a_20240115.jpg"
