import json
from pathlib import Path

import cv2

from iot.pipeline import run_pipeline
from iot.tile_quality import BLACK_RATIO_THRESHOLD, check_tile_integrity


DATA_DIR = Path("data")
SAMPLE_PAYLOADS = DATA_DIR / "payloads_BR-MT-001.json"


def _target_frame(frame_reference: str) -> str:
    return frame_reference.split(">", 1)[1]


def test_black_mt_frame_is_invalid():
    frame = cv2.imread(str(DATA_DIR / "frame_mt_20240930.jpg"))

    result = check_tile_integrity(frame)

    assert result["passes"] is False
    assert result["black_ratio"] > BLACK_RATIO_THRESHOLD


def test_sample_payloads_match_current_pipeline_output():
    payloads = json.loads(SAMPLE_PAYLOADS.read_text(encoding="utf-8"))
    regenerated = run_pipeline(str(DATA_DIR), "BR-MT-001", "Sentinel-2")

    assert len(payloads) == len(regenerated)
    assert [p["frame_reference"] for p in payloads] == [
        p["frame_reference"] for p in regenerated
    ]


def test_sample_payloads_use_class_percentage_contract_scale():
    payloads = json.loads(SAMPLE_PAYLOADS.read_text(encoding="utf-8"))

    for payload in payloads:
        assert 0.0 <= payload["class_percentage"] <= 100.0
        assert payload["class_percentage"] > 1.0


def test_sample_payloads_do_not_reference_invalid_black_tiles_without_fallback():
    payloads = json.loads(SAMPLE_PAYLOADS.read_text(encoding="utf-8"))

    for payload in payloads:
        target = _target_frame(payload["frame_reference"])
        if target.startswith("alt:"):
            continue

        frame = cv2.imread(str(DATA_DIR / target))
        result = check_tile_integrity(frame)

        assert result["black_ratio"] <= BLACK_RATIO_THRESHOLD, payload["frame_reference"]
        assert "tile_quality" in payload
        assert payload["tile_quality"]["black_ratio"] <= BLACK_RATIO_THRESHOLD


def test_sample_payloads_do_not_keep_black_tile_false_positive():
    payloads = json.loads(SAMPLE_PAYLOADS.read_text(encoding="utf-8"))

    assert all(
        not (
            payload["frame_reference"].endswith(">frame_mt_20240930.jpg")
            and payload["detected_class"] == "queimada"
        )
        for payload in payloads
    )
