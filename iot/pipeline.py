import json
import os
import re
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import cv2

from iot.change_detector import compute_change_score
from iot.detector import detect_class
from iot.payload import build_payload
from iot.quality import compute_quality_metrics
from iot.tile_fetcher import fetch_best_tile
from iot.tile_quality import check_tile_integrity

_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
_FRAME_SOURCES_FILE = "frame_sources.json"
_DATE_COMPACT_RE = re.compile(r'(\d{4})(\d{2})(\d{2})')
_DATE_ISO_RE = re.compile(r'(\d{4})-(\d{2})-(\d{2})')
_GIBS_TILE_RE = re.compile(r"/(?P<resolution>\d+m)/(?P<zoom>\d+)/(?P<row>\d+)/(?P<col>\d+)(?:\.[^/?#]+)?")


def _filename_date(name: str) -> Optional[str]:
    """Return 'YYYY-MM-DD' extracted from YYYYMMDD or YYYY-MM-DD in a filename."""
    iso = _DATE_ISO_RE.search(name)
    if iso:
        return f"{iso.group(1)}-{iso.group(2)}-{iso.group(3)}"

    compact = _DATE_COMPACT_RE.search(name)
    if compact:
        return f"{compact.group(1)}-{compact.group(2)}-{compact.group(3)}"
    return None


def _date_offsets(max_days: int):
    yield 0
    for days in range(1, max_days + 1):
        yield -days
        yield days


def _normalize_date(value: Optional[str]) -> str:
    if not value:
        return "2000-01-01"

    parsed = _filename_date(value)
    if parsed:
        return parsed

    try:
        return datetime.strptime(value, "%Y-%m-%d").strftime("%Y-%m-%d")
    except ValueError:
        return "2000-01-01"


def _derive_url_template(url: str) -> Optional[str]:
    if "{date}" in url:
        return url

    match = _DATE_ISO_RE.search(url)
    if match:
        return f"{url[:match.start()]}{{date}}{url[match.end():]}"

    return None


def _tile_coords_from_url(url: str) -> Dict[str, int | str]:
    match = _GIBS_TILE_RE.search(url)
    if not match:
        return {}

    return {
        "resolution": match.group("resolution"),
        "zoom": int(match.group("zoom")),
        "row": int(match.group("row")),
        "col": int(match.group("col")),
    }


def _load_frame_metadata(frames_folder: str) -> Dict[str, Dict[str, Any]]:
    path = os.path.join(frames_folder, _FRAME_SOURCES_FILE)
    if not os.path.exists(path):
        return {}

    try:
        with open(path) as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}

    metadata: Dict[str, Dict[str, Any]] = {}
    for filename, meta in data.items():
        if isinstance(meta, str):
            normalized: Dict[str, Any] = {"url": meta}
        else:
            normalized = dict(meta)

        template = normalized.get("url_template") or _derive_url_template(normalized.get("url", ""))
        if template and "{date}" in template:
            normalized["url_template"] = template

        metadata[filename] = normalized

    return metadata


def _tile_record(
    filename: Optional[str],
    pipeline_source: str,
    date_used: str,
    integrity: dict,
    metadata: Optional[Dict[str, Any]] = None,
    url: Optional[str] = None,
) -> Dict[str, Any]:
    meta = metadata or {}
    record: Dict[str, Any] = {
        "source": meta.get("source") or pipeline_source,
        "date_used": date_used,
        "check_tile_integrity": dict(integrity),
        "black_ratio": float(integrity["black_ratio"]),
    }

    if filename:
        record["filename"] = filename

    url_used = url or meta.get("url")
    template = meta.get("url_template")
    if not url_used and template and "{date}" in template:
        url_used = template.replace("{date}", date_used)

    if url_used:
        record["url"] = url_used
        for key, value in _tile_coords_from_url(url_used).items():
            record.setdefault(key, value)

    if template:
        record["url_template"] = template

    datetime_used = meta.get("datetime")
    if datetime_used:
        record["datetime"] = datetime_used

    for key in ("row", "col", "bbox", "zoom", "resolution"):
        if key in meta and meta[key] not in (None, ""):
            record[key] = meta[key]

    return record


def _build_tile_quality(selected_tile: Dict[str, Any], fallback: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    tile_quality: Dict[str, Any] = {
        "black_ratio": selected_tile["black_ratio"],
        "date_used": selected_tile["date_used"],
        "source": selected_tile["source"],
        "check_tile_integrity": selected_tile["check_tile_integrity"],
        "selected_tile": selected_tile,
        "fallback": fallback or {"used": False},
    }

    if "url" in selected_tile:
        tile_quality["url_used"] = selected_tile["url"]

    for key in ("row", "col", "bbox", "zoom", "resolution"):
        if key in selected_tile:
            tile_quality[key] = selected_tile[key]

    return tile_quality


def _find_local_alt_tile(
    frames_folder: str,
    current_name: str,
    base_date: str,
    max_days_offset: int = 3,
):
    try:
        base = datetime.strptime(base_date, "%Y-%m-%d")
    except ValueError:
        return None, None, None, None

    candidates = sorted(
        f for f in os.listdir(frames_folder)
        if f != current_name and os.path.splitext(f)[1].lower() in _IMAGE_EXTENSIONS
    )

    for offset in _date_offsets(max_days_offset):
        target = base + timedelta(days=offset)
        date_iso = target.strftime("%Y-%m-%d")
        date_compact = target.strftime("%Y%m%d")

        for filename in candidates:
            if date_compact not in filename and date_iso not in filename:
                continue

            frame = cv2.imread(os.path.join(frames_folder, filename))
            if frame is None:
                continue

            integrity = check_tile_integrity(frame)
            if integrity["passes"]:
                return frame, date_iso, integrity, filename

    return None, None, None, None


def run_pipeline(
    frames_folder: str,
    area_id: str,
    source: str,
    url_templates: Optional[Dict[str, str]] = None,
) -> List[dict]:
    """Process consecutive frame pairs from a folder and return validated payloads."""
    if not os.path.exists(frames_folder):
        raise FileNotFoundError(f"Folder not found: {frames_folder}")

    frame_metadata = _load_frame_metadata(frames_folder)
    remote_templates = {
        filename: meta["url_template"]
        for filename, meta in frame_metadata.items()
        if meta.get("url_template")
    }
    if url_templates:
        for filename, template in url_templates.items():
            frame_metadata.setdefault(filename, {})["url_template"] = template
        remote_templates.update(url_templates)

    entries = sorted(
        f for f in os.listdir(frames_folder)
        if os.path.splitext(f)[1].lower() in _IMAGE_EXTENSIONS
    )

    frames = []
    for filename in entries:
        img = cv2.imread(os.path.join(frames_folder, filename))
        if img is not None:
            frames.append((filename, img))

    payloads = []
    for i in range(len(frames) - 1):
        name_a, frame_a = frames[i]
        name_b, frame_b = frames[i + 1]

        integrity = check_tile_integrity(frame_b)
        frame_reference = f"{name_a}>{name_b}"
        date_b = _normalize_date(_filename_date(name_b))
        original_tile = _tile_record(
            filename=name_b,
            pipeline_source=source,
            date_used=date_b,
            integrity=integrity,
            metadata=frame_metadata.get(name_b),
        )
        selected_tile = original_tile
        fallback_evidence: Optional[Dict[str, Any]] = None

        if not integrity["passes"]:
            base_date = date_b
            alt_frame, date_used, alt_integrity, alt_filename = _find_local_alt_tile(
                frames_folder,
                name_b,
                base_date,
            )

            if alt_frame is None:
                url_template = remote_templates.get(name_b)
                if not url_template or "{date}" not in url_template:
                    print(f"[pipeline] {name_b}: sem url_template remoto para fallback, ignorando")
                    continue

                alt_frame, date_used = fetch_best_tile(url_template, base_date)
                alt_integrity = check_tile_integrity(alt_frame) if alt_frame is not None else None
                alt_filename = None

            if alt_frame is None:
                print(f"[pipeline] {name_b}: sem tile válido, ignorando")
                continue

            if not alt_integrity or not alt_integrity["passes"]:
                print(f"[pipeline] {name_b}: tile alternativo inválido, ignorando")
                continue

            date_used = _normalize_date(date_used)
            frame_b = alt_frame
            frame_reference = f"{name_a}>alt:{date_used}"
            alt_meta = frame_metadata.get(alt_filename or "", {})
            alt_url = None
            if name_b in remote_templates:
                alt_url = remote_templates[name_b].replace("{date}", date_used)
                alt_meta = {
                    **frame_metadata.get(name_b, {}),
                    **alt_meta,
                    "url_template": remote_templates[name_b],
                }
            selected_tile = _tile_record(
                filename=alt_filename,
                pipeline_source=source,
                date_used=date_used,
                integrity=alt_integrity,
                metadata=alt_meta,
                url=alt_url,
            )
            fallback_evidence = {
                "used": True,
                "original_rejected": original_tile,
                "alternative_used": selected_tile,
            }

        change_score = compute_change_score(frame_a, frame_b)
        quality_result = compute_quality_metrics(frame_b)
        detector_result = detect_class(frame_b)
        tile_quality = _build_tile_quality(selected_tile, fallback_evidence)
        tile_quality["detected_class"] = detector_result["detected_class"]
        tile_quality["class_percentage"] = float(detector_result["class_percentage"])
        tile_quality["selected_tile"]["detected_class"] = detector_result["detected_class"]
        tile_quality["selected_tile"]["class_percentage"] = float(detector_result["class_percentage"])

        payload = build_payload(
            event_id=str(uuid.uuid4()),
            area_id=area_id,
            source=source,
            detector_result=detector_result,
            quality_result=quality_result,
            change_score=change_score,
            frame_reference=frame_reference,
        )
        payload["tile_quality"] = tile_quality
        payloads.append(payload)

    return payloads
