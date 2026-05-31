#!/usr/bin/env python3
"""Semantic gate for versioned orbital sample data and mobile mocks."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from iot.tile_quality import BLACK_RATIO_THRESHOLD, check_tile_integrity


MIN_ALERTS = 5
MIN_CLASSES = 4
REQUIRED_RISK_LEVELS = {"baixo", "medio", "alto"}
ALLOWED_CLASSES = {"vegetacao", "solo_exposto", "agua", "queimada", "baixa_visibilidade"}
REQUIRED_MOCK_FIELDS = {
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
    "source",
    "image_url",
}

GIBS_VISUAL_PRODUCT = "MODIS_Terra_CorrectedReflectance_TrueColor"
GIBS_TILE_PROVIDER = "NASA GIBS"


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _is_percentage(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return 0.0 <= number <= 100.0


def _frame_target(frame_reference: str) -> str:
    return frame_reference.split(">", 1)[1] if ">" in frame_reference else frame_reference


def _fallback_registered(payload: dict[str, Any]) -> bool:
    fallback = payload.get("tile_quality", {}).get("fallback", {})
    return bool(fallback.get("used") is True and fallback.get("alternative_used"))


def _black_ratio_from_frame(path: Path) -> float | None:
    frame = cv2.imread(str(path))
    if frame is None:
        return None
    return float(check_tile_integrity(frame)["black_ratio"])


def _infer_source_from_url(url: str) -> str | None:
    lowered = url.lower()
    if "gibs.earthdata.nasa.gov" in lowered and GIBS_VISUAL_PRODUCT.lower() in lowered:
        return "MODIS/GIBS"
    if "sentinel-2" in lowered or "sentinel2" in lowered:
        return "Sentinel-2"
    if "landsat" in lowered or "usgs.gov" in lowered:
        return "Landsat"
    if "firms" in lowered:
        return "FIRMS"
    if "inpe" in lowered or "brazildatacube" in lowered:
        return "INPE"
    return None


def _source_matches(expected: str, declared: str) -> bool:
    if expected == "Sentinel-2":
        return declared == "Sentinel-2" or declared.startswith("Sentinel-")
    if expected == "Landsat":
        return declared == "Landsat" or declared.startswith("Landsat-")
    return declared == expected


def _source_url_errors(label: str, item: dict[str, Any], source_key: str, url_key: str) -> list[str]:
    source = str(item.get(source_key, "") or "")
    url = str(item.get(url_key, "") or "")
    if not source or not url:
        return []

    expected = _infer_source_from_url(url)
    if expected is None or _source_matches(expected, source):
        return []

    return [f"{label}: source {source!r} is incoherent with verifiable URL source {expected!r}"]


def _payload_url_pairs(payload: dict[str, Any]) -> list[tuple[str, dict[str, Any], str, str]]:
    event_id = payload.get("event_id", "<sem event_id>")
    pairs: list[tuple[str, dict[str, Any], str, str]] = []
    for key in ("image_url", "tile_url", "url"):
        if key in payload:
            pairs.append((f"{event_id}.{key}", payload, "source", key))

    tile_quality = payload.get("tile_quality")
    if isinstance(tile_quality, dict):
        if "url_used" in tile_quality:
            pairs.append((f"{event_id}.tile_quality.url_used", tile_quality, "source", "url_used"))
        selected = tile_quality.get("selected_tile")
        if isinstance(selected, dict) and "url" in selected:
            pairs.append((f"{event_id}.tile_quality.selected_tile.url", selected, "source", "url"))
        fallback = tile_quality.get("fallback")
        if isinstance(fallback, dict):
            for name in ("original_rejected", "alternative_used"):
                item = fallback.get(name)
                if isinstance(item, dict) and "url" in item:
                    pairs.append((f"{event_id}.tile_quality.fallback.{name}.url", item, "source", "url"))
    return pairs


def validate_payload_file(path: Path, data_dir: Path | None = None) -> list[str]:
    data_dir = data_dir or path.parent
    errors: list[str] = []
    payloads = _read_json(path)
    if not isinstance(payloads, list):
        return [f"{path}: expected a JSON array"]

    for index, payload in enumerate(payloads):
        if not isinstance(payload, dict):
            errors.append(f"{path}:{index}: expected object payload")
            continue

        label = str(payload.get("event_id", f"{path.name}[{index}]"))
        if not _is_percentage(payload.get("class_percentage")):
            errors.append(f"{label}: class_percentage must be in 0-100 scale")

        frame_reference = payload.get("frame_reference")
        tile_quality = payload.get("tile_quality", {})
        if not frame_reference:
            errors.append(f"{label}: missing frame_reference")
        else:
            target = _frame_target(str(frame_reference))
            if target.startswith("alt:"):
                if not _fallback_registered(payload):
                    errors.append(f"{label}: alt frame used without fallback metadata")
                selected_black_ratio = float(tile_quality.get("black_ratio", 0.0) or 0.0)
                if selected_black_ratio > BLACK_RATIO_THRESHOLD:
                    errors.append(f"{label}: fallback selected tile black_ratio={selected_black_ratio:.2f}")
            else:
                frame_path = data_dir / target
                black_ratio = _black_ratio_from_frame(frame_path)
                if black_ratio is None:
                    errors.append(f"{label}: frame_reference target not readable: {target}")
                elif black_ratio > BLACK_RATIO_THRESHOLD and not _fallback_registered(payload):
                    errors.append(
                        f"{label}: frame {target} has black_ratio={black_ratio:.2f} "
                        "without fallback metadata"
                    )

        if isinstance(tile_quality, dict):
            selected_percentage = tile_quality.get("class_percentage")
            if selected_percentage is not None and not _is_percentage(selected_percentage):
                errors.append(f"{label}: tile_quality.class_percentage must be in 0-100 scale")

        for pair_label, item, source_key, url_key in _payload_url_pairs(payload):
            errors.extend(_source_url_errors(pair_label, item, source_key, url_key))

    return errors


def _parse_ts_value(raw: str) -> Any:
    raw = raw.strip().rstrip(",")
    if raw.startswith("'") and raw.endswith("'"):
        return raw[1:-1].replace("\\'", "'").replace("\\\\", "\\")
    try:
        return float(raw)
    except ValueError:
        return raw


def parse_generated_mock_alerts(path: Path) -> list[dict[str, Any]]:
    content = path.read_text(encoding="utf-8")
    alerts: list[dict[str, Any]] = []
    for block in re.findall(r"  \{\n(.*?)\n  \}", content, flags=re.DOTALL):
        alert: dict[str, Any] = {}
        for line in block.splitlines():
            match = re.match(r"\s*(\w+):\s*(.+),\s*$", line)
            if match:
                alert[match.group(1)] = _parse_ts_value(match.group(2))
        if alert:
            alerts.append(alert)
    return alerts


def validate_mock_alerts(alerts: list[dict[str, Any]], label: str = "generatedMockData") -> list[str]:
    errors: list[str] = []
    if len(alerts) < MIN_ALERTS:
        errors.append(f"{label}: expected at least {MIN_ALERTS} alerts, got {len(alerts)}")

    risk_levels = {a.get("risk_level") for a in alerts}
    missing_risk = REQUIRED_RISK_LEVELS - risk_levels
    if missing_risk:
        errors.append(f"{label}: missing risk_level coverage: {', '.join(sorted(missing_risk))}")

    classes = {a.get("detected_class") for a in alerts}
    covered_classes = classes & ALLOWED_CLASSES
    if len(covered_classes) < MIN_CLASSES:
        errors.append(
            f"{label}: expected at least {MIN_CLASSES} classes, got {len(covered_classes)}"
        )

    for index, alert in enumerate(alerts):
        event_id = str(alert.get("event_id", f"{label}[{index}]"))
        missing = REQUIRED_MOCK_FIELDS - set(alert)
        if missing:
            errors.append(f"{event_id}: missing mock fields: {', '.join(sorted(missing))}")
        if alert.get("risk_level") not in REQUIRED_RISK_LEVELS:
            errors.append(f"{event_id}: invalid risk_level {alert.get('risk_level')!r}")
        if alert.get("detected_class") not in ALLOWED_CLASSES:
            errors.append(f"{event_id}: invalid detected_class {alert.get('detected_class')!r}")
        if not _is_percentage(alert.get("class_percentage")):
            errors.append(f"{event_id}: class_percentage must be in 0-100 scale")
        errors.extend(_source_url_errors(event_id, alert, "source", "image_url"))
        if _infer_source_from_url(str(alert.get("image_url", ""))) == "MODIS/GIBS":
            if alert.get("visual_product") != GIBS_VISUAL_PRODUCT:
                errors.append(f"{event_id}: missing MODIS/GIBS visual_product")
            if alert.get("tile_provider") != GIBS_TILE_PROVIDER:
                errors.append(f"{event_id}: missing NASA GIBS tile_provider")

    return errors


def validate_generated_mock_file(path: Path) -> list[str]:
    return validate_mock_alerts(parse_generated_mock_alerts(path), str(path))


def validate_mock_evidence_file(path: Path) -> list[str]:
    errors: list[str] = []
    evidence = _read_json(path)
    if not isinstance(evidence, list):
        return [f"{path}: expected a JSON array"]

    for index, item in enumerate(evidence):
        if not isinstance(item, dict):
            errors.append(f"{path}:{index}: expected object evidence")
            continue
        label = str(item.get("event_id", f"{path.name}[{index}]"))
        if not _is_percentage(item.get("class_percentage")):
            errors.append(f"{label}: evidence class_percentage must be in 0-100 scale")
        black_ratio = float(item.get("black_ratio", 0.0) or 0.0)
        fallback = item.get("fallback", {})
        if black_ratio > BLACK_RATIO_THRESHOLD and not (
            isinstance(fallback, dict) and fallback.get("used") is True
        ):
            errors.append(f"{label}: evidence black_ratio={black_ratio:.2f} without fallback")
        errors.extend(_source_url_errors(label, item, "source", "url"))
    return errors


def validate_all(root: Path) -> list[str]:
    errors: list[str] = []
    data_dir = root / "data"
    for payload_path in sorted(data_dir.glob("payloads_*.json")):
        errors.extend(validate_payload_file(payload_path, data_dir))

    evidence_path = data_dir / "generated_mock_tile_evidence.json"
    if evidence_path.exists():
        errors.extend(validate_mock_evidence_file(evidence_path))
    else:
        errors.append(f"{evidence_path}: missing generated mock evidence")

    generated_mock = root / "mobile" / "src" / "services" / "generatedMockData.ts"
    if generated_mock.exists():
        errors.extend(validate_generated_mock_file(generated_mock))
    else:
        errors.append(f"{generated_mock}: missing generated mobile mock")

    return errors


def validate_target(target: str, root: Path) -> list[str]:
    aliases = {"data", "mock", "mocks", "data/mock", "data-mock"}
    if target in aliases:
        return validate_all(root)

    path = (root / target).resolve()
    if not path.exists():
        return [f"{target}: target not found"]
    if path.is_dir():
        if path.name == "data":
            return validate_all(root)
        return [f"{target}: semantic data gate only supports data/mock targets"]
    if path.name.startswith("payloads_") and path.suffix == ".json":
        return validate_payload_file(path, path.parent)
    if path.name == "generated_mock_tile_evidence.json":
        return validate_mock_evidence_file(path)
    if path.name == "generatedMockData.ts":
        return validate_generated_mock_file(path)
    return [f"{target}: unsupported semantic data target"]


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    target = sys.argv[1] if len(sys.argv) > 1 else "data"
    errors = validate_target(target, root)
    if errors:
        for error in errors:
            print(f"semantic-data-gate: {error}", file=sys.stderr)
        return 1
    print(f"semantic-data-gate: OK ({target})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
