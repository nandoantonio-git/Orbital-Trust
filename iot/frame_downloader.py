import json
import os
import urllib.request
import urllib.error
from typing import List


def _traceable_filename(source: str, area_id: str, scene_id: str, url: str) -> str:
    ext = os.path.splitext(url.split("?")[0])[1] or ".jpg"
    safe = lambda s: s.replace("/", "-").replace(" ", "_").lower()
    return f"{safe(source)}__{safe(area_id)}__{safe(scene_id)}{ext}"


def download_scene_frames(manifest_path: str, output_folder: str) -> List[str]:
    with open(manifest_path) as f:
        manifest = json.load(f)

    os.makedirs(output_folder, exist_ok=True)
    downloaded: List[str] = []

    for scene in manifest.get("scenes", []):
        href: str = scene.get("asset_href", "")
        if not href:
            continue

        source = scene.get("source", "unknown")
        area_id = scene.get("area_id", manifest.get("area_id", "unknown"))
        scene_id = scene.get("scene_id", "unknown")

        filename = _traceable_filename(source, area_id, scene_id, href)
        dest = os.path.join(output_folder, filename)

        if os.path.exists(dest):
            downloaded.append(dest)
            continue

        try:
            urllib.request.urlretrieve(href, dest)
            downloaded.append(dest)
        except (urllib.error.URLError, OSError) as exc:
            print(f"[frame_downloader] failed to download {href}: {exc}")

    return downloaded
