import os
import tempfile
from typing import List

from iot.data_sources import SUPPORTED_SOURCES
from iot.frame_downloader import download_scene_frames
from iot.pipeline import run_pipeline
from iot.scene_manifest import build_scene_manifest
from iot.stac_client import search_scenes


def run_orbital_ingestion(
    area_id: str,
    bbox: List[float],
    start_date: str,
    end_date: str,
    source: str,
    _mock_stac_response=None,
    _mock_download=None,
) -> List[dict]:
    """Search STAC, build manifest, download frames, and run the IoT pipeline.

    Args:
        area_id: Identifier for the monitored area.
        bbox: [west, south, east, north] in WGS-84 degrees.
        start_date: ISO-8601 date string (e.g. "2024-01-01").
        end_date: ISO-8601 date string (e.g. "2024-01-31").
        source: One of SUPPORTED_SOURCES ("Sentinel-2", "Landsat", "FIRMS", "INPE").
        _mock_stac_response: If provided, skip HTTP STAC call (for testing).
        _mock_download: If provided, callable used instead of download_scene_frames (for testing).

    Returns:
        List of validated IoT payload dicts.
    """
    if source not in SUPPORTED_SOURCES:
        raise ValueError(f"source deve ser um de {SUPPORTED_SOURCES}, recebido: {source!r}")

    scenes = search_scenes(
        bbox=bbox,
        start_date=start_date,
        end_date=end_date,
        source=source,
        _mock_response=_mock_stac_response,
    )

    if not scenes:
        return []

    with tempfile.TemporaryDirectory() as tmp_dir:
        manifests_dir = os.path.join(tmp_dir, "manifests")
        os.makedirs(manifests_dir, exist_ok=True)
        frames_dir = os.path.join(tmp_dir, "frames")

        import iot.scene_manifest as _sm_module
        original_dir = _sm_module.MANIFESTS_DIR
        _sm_module.MANIFESTS_DIR = manifests_dir
        try:
            manifest = build_scene_manifest(scenes, area_id=area_id)
        finally:
            _sm_module.MANIFESTS_DIR = original_dir

        manifest_path = os.path.join(manifests_dir, f"{area_id}.json")

        if _mock_download is not None:
            _mock_download(manifest_path, frames_dir)
        else:
            download_scene_frames(manifest_path, frames_dir)

        payloads = run_pipeline(frames_dir, area_id=area_id, source=source)

    return payloads
