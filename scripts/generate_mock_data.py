#!/usr/bin/env python3
"""Generate mobile/src/services/generatedMockData.ts from real GIBS satellite tiles.

Searches for 1 valid tile per class, runs the IoT CV pipeline on it, and writes
the resulting AlertResponse objects to a TypeScript module.
"""

import ssl
import sys
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from urllib.request import Request, urlopen

import certifi
import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from api.main import analyze_alert
from iot.change_detector import compute_change_score
from iot.contract import CV_ALGORITHM_VERSION, IoTPayload
from iot.detector import detect_class
from iot.quality import compute_quality_metrics
from iot.tile_quality import check_tile_integrity

_SSL_CTX = ssl.create_default_context(cafile=certifi.where())

_GIBS_TEMPLATE = (
    "https://gibs.earthdata.nasa.gov/wmts/epsg4326/best"
    "/MODIS_Terra_CorrectedReflectance_TrueColor/default"
    "/{date}/250m/7/{row}/{col}.jpg"
)
GIBS_VISUAL_PRODUCT = "MODIS_Terra_CorrectedReflectance_TrueColor"
GIBS_TILE_PROVIDER = "NASA GIBS"
GIBS_SOURCE = "MODIS/GIBS"
CONTRACT_SOURCES = {"Sentinel-2", "Landsat", "FIRMS", "INPE"}

MIN_ALERTS = 5
MIN_CLASSES = 4
REQUIRED_RISK_LEVELS = {"baixo", "medio", "alto"}
ALLOWED_CLASSES = {"vegetacao", "solo_exposto", "agua", "queimada", "baixa_visibilidade"}
REQUIRED_ALERT_FIELDS = {
    "event_id",
    "timestamp",
    "detected_class",
    "risk_level",
    "analysis_confidence",
    "explanation",
    "recommendation",
    "model_version",
    "class_percentage",
    "change_score",
    "cloud_score",
    "shadow_score",
    "brightness_score",
    "blur_score",
    "image_quality",
    "cv_confidence",
    "algorithm_version",
    "source",
    "contract_source",
    "visual_product",
    "tile_provider",
    "image_url",
}
MOCK_EVIDENCE_PATH = Path(__file__).parent.parent / "data" / "generated_mock_tile_evidence.json"

# Target regions as WMTS tile coordinates (zoom=7, 250m)
TARGETS = [
    {
        "target_class": "queimada",
        "row": 37, "col": 44,
        "start_date": "2024-09-01",
        "area_id": "area-mato-grosso",
        "target_risk_level": "alto",
    },
    {
        "target_class": "solo_exposto",
        "row": 34, "col": 51,
        "start_date": "2024-08-01",
        "area_id": "area-sertao-ne",
        "target_risk_level": "medio",
    },
    {
        "target_class": "vegetacao",
        "row": 29, "col": 42,
        "start_date": "2024-07-01",
        "area_id": "area-para",
        "target_risk_level": "baixo",
    },
    {
        "target_class": "agua",
        "row": 39, "col": 43,
        "start_date": "2024-02-01",
        "area_id": "area-pantanal",
        "target_risk_level": "medio",
    },
    {
        "target_class": "vegetacao",
        "row": 29, "col": 42,
        "start_date": "2024-10-01",
        "area_id": "area-para-monitoramento",
        "target_risk_level": "baixo",
    },
]

def build_previous_frame_for_risk(curr_frame: np.ndarray, risk_level: str) -> np.ndarray:
    if risk_level == "baixo":
        return curr_frame.copy()
    gray = cv2.cvtColor(curr_frame, cv2.COLOR_BGR2GRAY).astype(np.int16)
    if risk_level == "medio":
        previous_gray = np.where(gray > 127, gray - 70, gray + 70)
        previous_gray = np.clip(previous_gray, 0, 255).astype(np.uint8)
        return np.repeat(previous_gray[:, :, None], 3, axis=2)
    if risk_level == "alto":
        previous_gray = np.where(gray > 127, 0, 255).astype(np.uint8)
        return np.repeat(previous_gray[:, :, None], 3, axis=2)
    raise ValueError("risk_level must be one of: baixo, medio, alto")


def _fetch_frame(row: int, col: int, date: str) -> Optional[np.ndarray]:
    url = _GIBS_TEMPLATE.format(date=date, row=row, col=col)
    try:
        req = Request(url)
        with urlopen(req, timeout=30, context=_SSL_CTX) as resp:
            data = resp.read()
        buf = np.frombuffer(data, dtype=np.uint8)
        return cv2.imdecode(buf, cv2.IMREAD_COLOR)
    except Exception:
        return None


def is_gibs_modis_url(image_url: str) -> bool:
    return "gibs.earthdata.nasa.gov" in image_url and GIBS_VISUAL_PRODUCT in image_url


def display_source_for_image(source: str, image_url: str) -> str:
    if is_gibs_modis_url(image_url) and _looks_like_contract_source(source):
        return GIBS_SOURCE
    return source


def _looks_like_contract_source(source: str) -> bool:
    return source in CONTRACT_SOURCES or source.startswith("Sentinel") or source.startswith("Landsat")


def _contract_source_for_analysis(source: str) -> str:
    if source in CONTRACT_SOURCES:
        return source
    if source.startswith("Sentinel"):
        return "Sentinel-2"
    if source.startswith("Landsat"):
        return "Landsat"
    return "FIRMS"


def build_alert_from_frames(
    curr_frame: np.ndarray,
    prev_frame: np.ndarray,
    image_url: str,
    date: str,
    area_id: str,
    source: str,
    event_index: int,
) -> dict:
    """Build an AlertResponse dict using real pipeline metrics from two frames."""
    change_score = compute_change_score(prev_frame, curr_frame)
    quality = compute_quality_metrics(curr_frame)
    cls_result = detect_class(curr_frame)

    detected_class = cls_result["detected_class"]
    class_percentage = round(float(cls_result["class_percentage"]), 2)
    display_source = display_source_for_image(source, image_url)
    analysis_payload = IoTPayload(
        event_id=f"EVT-{date}-{event_index:03d}",
        timestamp=f"{date}T12:00:00Z",
        area_id=area_id,
        source=_contract_source_for_analysis(source),
        detected_class=detected_class,
        class_percentage=class_percentage,
        change_score=change_score,
        cloud_score=quality["cloud_score"],
        shadow_score=quality["shadow_score"],
        brightness_score=quality["brightness_score"],
        blur_score=quality["blur_score"],
        image_quality=quality["image_quality"],
        cv_confidence=quality["cv_confidence"],
        frame_reference=image_url,
        algorithm_version=CV_ALGORITHM_VERSION,
    )
    alert = analyze_alert(analysis_payload).model_dump()

    alert["source"] = display_source
    alert["visual_product"] = GIBS_VISUAL_PRODUCT if is_gibs_modis_url(image_url) else display_source
    alert["tile_provider"] = GIBS_TILE_PROVIDER if is_gibs_modis_url(image_url) else ""
    alert["image_url"] = image_url
    return alert


def build_mock_tile_evidence(
    alert: dict,
    area_id: str,
    row: int,
    col: int,
    date: str,
    image_url: str,
    integrity: dict,
    detector_result: dict,
) -> dict:
    return {
        "event_id": alert["event_id"],
        "area_id": area_id,
        "source": alert["source"],
        "visual_product": alert["visual_product"],
        "tile_provider": alert["tile_provider"],
        "url": image_url,
        "date_used": date,
        "row": row,
        "col": col,
        "black_ratio": float(integrity["black_ratio"]),
        "check_tile_integrity": dict(integrity),
        "detected_class": detector_result["detected_class"],
        "class_percentage": float(detector_result["class_percentage"]),
    }


def validate_minimum_coverage(alerts: list[dict]) -> list[str]:
    errors = []

    if len(alerts) < MIN_ALERTS:
        errors.append(f"expected at least {MIN_ALERTS} alerts, got {len(alerts)}")

    missing_by_alert = [
        f"{a.get('event_id', '<sem event_id>')}: {', '.join(sorted(REQUIRED_ALERT_FIELDS - set(a)))}"
        for a in alerts
        if REQUIRED_ALERT_FIELDS - set(a)
    ]
    if missing_by_alert:
        errors.append("alerts with missing required fields: " + "; ".join(missing_by_alert))

    risk_levels = {a.get("risk_level") for a in alerts}
    missing_risk = REQUIRED_RISK_LEVELS - risk_levels
    if missing_risk:
        errors.append("missing risk_level coverage: " + ", ".join(sorted(missing_risk)))

    image_qualities = {a.get("image_quality") for a in alerts}
    if "baixa" not in image_qualities:
        errors.append("missing image_quality coverage: baixa")

    detected_classes = {a.get("detected_class") for a in alerts}
    covered_classes = detected_classes & ALLOWED_CLASSES
    if len(covered_classes) < MIN_CLASSES:
        errors.append(
            f"expected at least {MIN_CLASSES} detected classes, got "
            f"{len(covered_classes)} ({', '.join(sorted(covered_classes)) or 'none'})"
        )

    invalid_classes = detected_classes - ALLOWED_CLASSES
    if invalid_classes:
        errors.append("invalid detected_class values: " + ", ".join(sorted(map(str, invalid_classes))))

    for alert in alerts:
        source = str(alert.get("source", ""))
        image_url = str(alert.get("image_url", ""))
        if is_gibs_modis_url(image_url):
            if _looks_like_contract_source(source):
                errors.append(
                    f"{alert.get('event_id', '<sem event_id>')}: source {source!r} "
                    "is incoherent with MODIS/GIBS image_url"
                )
            if alert.get("visual_product") != GIBS_VISUAL_PRODUCT:
                errors.append(
                    f"{alert.get('event_id', '<sem event_id>')}: missing MODIS visual_product"
                )
            if alert.get("tile_provider") != GIBS_TILE_PROVIDER:
                errors.append(
                    f"{alert.get('event_id', '<sem event_id>')}: missing NASA GIBS tile_provider"
                )

    return errors


def assert_minimum_coverage(alerts: list[dict]) -> None:
    errors = validate_minimum_coverage(alerts)
    if errors:
        raise ValueError("mock data coverage failed: " + " | ".join(errors))


def _escape_ts(s: str) -> str:
    return s.replace("\\", "\\\\").replace("'", "\\'")


def format_ts_file(alerts: list) -> str:
    # tile evidence is written to data/generated_mock_tile_evidence.json, not AlertResponse.
    lines = [
        "import { AlertResponse } from '../types/alert';",
        "",
        "// Generated by scripts/generate_mock_data.py — do not edit manually",
        "export const generatedAlerts: AlertResponse[] = [",
    ]
    for a in alerts:
        lines.append("  {")
        lines.append(f"    event_id: '{_escape_ts(a['event_id'])}',")
        lines.append(f"    timestamp: '{_escape_ts(a['timestamp'])}',")
        lines.append(f"    detected_class: '{_escape_ts(a['detected_class'])}',")
        lines.append(f"    risk_level: '{_escape_ts(a['risk_level'])}',")
        lines.append(f"    analysis_confidence: {a['analysis_confidence']},")
        lines.append(f"    explanation: '{_escape_ts(a['explanation'])}',")
        lines.append(f"    recommendation: '{_escape_ts(a['recommendation'])}',")
        lines.append(f"    model_version: '{_escape_ts(a['model_version'])}',")
        lines.append(f"    class_percentage: {a['class_percentage']},")
        lines.append(f"    change_score: {a['change_score']},")
        if "cloud_score" in a:
            lines.append(f"    cloud_score: {a['cloud_score']},")
        if "shadow_score" in a:
            lines.append(f"    shadow_score: {a['shadow_score']},")
        if "brightness_score" in a:
            lines.append(f"    brightness_score: {a['brightness_score']},")
        if "blur_score" in a:
            lines.append(f"    blur_score: {a['blur_score']},")
        if "image_quality" in a:
            lines.append(f"    image_quality: '{_escape_ts(a['image_quality'])}',")
        if "cv_confidence" in a:
            lines.append(f"    cv_confidence: {a['cv_confidence']},")
        if "algorithm_version" in a:
            lines.append(f"    algorithm_version: '{_escape_ts(a['algorithm_version'])}',")
        lines.append(f"    source: '{_escape_ts(a['source'])}',")
        if "contract_source" in a:
            lines.append(f"    contract_source: '{_escape_ts(a['contract_source'])}',")
        lines.append(f"    visual_product: '{_escape_ts(a['visual_product'])}',")
        lines.append(f"    tile_provider: '{_escape_ts(a['tile_provider'])}',")
        lines.append(f"    image_url: '{_escape_ts(a['image_url'])}',")
        lines.append("  },")
    lines.append("];")
    return "\n".join(lines)


def write_mock_evidence(evidence: list[dict], output_path: Path = MOCK_EVIDENCE_PATH) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(evidence, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _date_offsets(max_days: int):
    yield 0
    for d in range(1, max_days + 1):
        yield -d
        yield d


def find_and_process_tile(
    target_class: str,
    row: int,
    col: int,
    start_date: str,
    area_id: str,
    source: str,
    event_index: int,
    target_risk_level: Optional[str] = None,
    max_days: int = 90,
) -> Optional[dict]:
    """Search for a valid tile matching target_class, run the pipeline, return AlertResponse."""
    base = datetime.strptime(start_date, "%Y-%m-%d")

    for offset in _date_offsets(max_days):
        candidate = base + timedelta(days=offset)
        date_str = candidate.strftime("%Y-%m-%d")

        curr_frame = _fetch_frame(row, col, date_str)
        if curr_frame is None:
            continue

        integrity = check_tile_integrity(curr_frame)
        if not integrity["passes"]:
            print(f"[{target_class}] {date_str}: black tile SKIP")
            continue

        cls_result = detect_class(curr_frame)
        if cls_result["detected_class"] != target_class:
            continue

        if target_risk_level:
            prev_frame = build_previous_frame_for_risk(curr_frame, target_risk_level)
        else:
            # Fetch previous day for change_score computation
            prev_date = (candidate - timedelta(days=1)).strftime("%Y-%m-%d")
            prev_frame = _fetch_frame(row, col, prev_date)
        if prev_frame is None:
            rng = np.random.RandomState(42)
            noise = rng.randint(-5, 6, curr_frame.shape, dtype=np.int16)
            prev_frame = np.clip(curr_frame.astype(np.int16) + noise, 0, 255).astype(np.uint8)

        url = _GIBS_TEMPLATE.format(date=date_str, row=row, col=col)
        print(f"[{target_class}] Found: {date_str}")
        alert = build_alert_from_frames(
            curr_frame=curr_frame,
            prev_frame=prev_frame,
            image_url=url,
            date=date_str,
            area_id=area_id,
            source=source,
            event_index=event_index,
        )
        alert["_tile_evidence"] = build_mock_tile_evidence(
            alert=alert,
            area_id=area_id,
            row=row,
            col=col,
            date=date_str,
            image_url=url,
            integrity=integrity,
            detector_result=cls_result,
        )
        return alert

    print(f"[{target_class}] No tile found within {max_days} days")
    return None


def main() -> None:
    alerts = []
    evidence = []
    for i, target in enumerate(TARGETS, start=1):
        print(f"\nSearching for {target['target_class']}...")
        alert = find_and_process_tile(
            target_class=target["target_class"],
            row=target["row"],
            col=target["col"],
            start_date=target["start_date"],
            area_id=target["area_id"],
            source=target.get("source", GIBS_SOURCE),
            event_index=i,
            target_risk_level=target.get("target_risk_level"),
        )
        if alert:
            tile_evidence = alert.pop("_tile_evidence", None)
            if tile_evidence:
                evidence.append(tile_evidence)
            alerts.append(alert)

    try:
        assert_minimum_coverage(alerts)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    ts_content = format_ts_file(alerts)
    output_path = (
        Path(__file__).parent.parent / "mobile" / "src" / "services" / "generatedMockData.ts"
    )
    output_path.write_text(ts_content, encoding="utf-8")
    write_mock_evidence(evidence)
    print(f"\nGenerated {output_path} with {len(alerts)} alerts")
    print(f"Generated {MOCK_EVIDENCE_PATH} with {len(evidence)} evidence records")


if __name__ == "__main__":
    main()
