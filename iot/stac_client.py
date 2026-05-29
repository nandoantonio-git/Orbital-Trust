from typing import Any, Dict, List, Optional
from urllib.request import urlopen, Request
from urllib.parse import urlencode
import json
import ssl
import certifi

_SSL_CTX = ssl.create_default_context(cafile=certifi.where())

from iot.data_sources import INPE_BDC_STAC_URL, COPERNICUS_STAC_URL


def _stac_url_for_source(source: str) -> str:
    if source in ("Sentinel-2", "FIRMS"):
        return COPERNICUS_STAC_URL
    return INPE_BDC_STAC_URL


def _collection_for_source(source: str) -> str:
    mapping = {
        "Sentinel-2": "SENTINEL-2",
        "Landsat": "LANDSAT-8-OLI",
        "FIRMS": "FIRMS",
        "INPE": "CBERS4A-WPM",
    }
    return mapping.get(source, source)


def _normalize_item(item: Dict[str, Any], source: str) -> Dict[str, Any]:
    props = item.get("properties", {})
    return {
        "scene_id": item.get("id", ""),
        "source": source,
        "datetime": props.get("datetime", ""),
        "cloud_score": float(props.get("eo:cloud_cover", 0.0)),
        "assets": {k: v.get("href", "") for k, v in item.get("assets", {}).items()},
    }


def search_scenes(
    bbox: List[float],
    start_date: str,
    end_date: str,
    source: str,
    max_cloud_score: float = 30.0,
    _mock_response: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Search STAC catalog for orbital scenes matching the given criteria.

    Args:
        bbox: [west, south, east, north] in WGS-84 degrees.
        start_date: ISO-8601 date string (e.g. "2024-01-01").
        end_date: ISO-8601 date string (e.g. "2024-01-31").
        source: One of SUPPORTED_SOURCES ("Sentinel-2", "Landsat", "FIRMS", "INPE").
        max_cloud_score: Maximum acceptable cloud cover percentage (0–100).
        _mock_response: If provided, skip HTTP call and use this as the STAC response.

    Returns:
        List of dicts with keys: scene_id, source, datetime, cloud_score, assets.
    """
    if _mock_response is not None:
        items = _mock_response.get("features", [])
        scenes = [_normalize_item(item, source) for item in items]
        return [s for s in scenes if s["cloud_score"] <= max_cloud_score]

    base_url = _stac_url_for_source(source)
    collection = _collection_for_source(source)
    endpoint = f"{base_url}/search"

    payload = json.dumps({
        "bbox": bbox,
        "datetime": f"{start_date}T00:00:00Z/{end_date}T23:59:59Z",
        "collections": [collection],
        "query": {"eo:cloud_cover": {"lte": max_cloud_score}},
        "limit": 100,
    }).encode()

    req = Request(endpoint, data=payload, headers={"Content-Type": "application/json"})
    with urlopen(req, timeout=30, context=_SSL_CTX) as resp:
        data: Dict[str, Any] = json.loads(resp.read())

    items = data.get("features", [])
    return [_normalize_item(item, source) for item in items]
