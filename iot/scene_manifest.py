from typing import Any, Dict, List, Optional
import json
import os
from datetime import datetime, timezone

_VISUAL_ASSET_KEYS = ("visual", "thumbnail", "TCI", "preview", "overview")

MANIFESTS_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "manifests")


def _select_asset_href(assets: Dict[str, str]) -> str:
    for key in _VISUAL_ASSET_KEYS:
        if key in assets:
            return assets[key]
    return next(iter(assets.values()), "")


def build_scene_manifest(scenes: List[Dict[str, Any]], area_id: str) -> dict:
    entries = []
    for scene in scenes:
        entries.append({
            "area_id": area_id,
            "source": scene.get("source", ""),
            "scene_id": scene.get("scene_id", ""),
            "datetime": scene.get("datetime", ""),
            "cloud_score": scene.get("cloud_score", 0.0),
            "asset_href": _select_asset_href(scene.get("assets", {})),
        })

    manifest = {
        "area_id": area_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scenes": entries,
    }

    os.makedirs(MANIFESTS_DIR, exist_ok=True)
    path = os.path.join(MANIFESTS_DIR, f"{area_id}.json")
    with open(path, "w") as f:
        json.dump(manifest, f, indent=2)

    return manifest
