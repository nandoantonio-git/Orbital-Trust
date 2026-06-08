import subprocess
import sys
from pathlib import Path

import numpy as np

import iot.demo_video as demo_video
from iot.visual_fallback import penalize_quality_for_fallback


def test_demo_video_uses_tasks_api_without_solutions() -> None:
    source = Path("iot/demo_video.py").read_text(encoding="utf-8")
    forbidden_api = "mp" + ".solutions" + ".selfie" + "_segmentation"

    assert forbidden_api not in source
    assert "ImageSegmenter" in source
    assert "BaseOptions" in source
    assert "RunningMode" in source


def test_demo_video_marks_local_score_as_non_official_visual_preview() -> None:
    source = Path("iot/demo_video.py").read_text(encoding="utf-8")

    assert "def _derive_risk" not in source
    assert "_derive_visual_preview" in source
    assert "nao oficial" in source
    assert "Risco:" not in source


def test_ensure_model_downloads_missing_file(monkeypatch, tmp_path: Path) -> None:
    model_path = tmp_path / "iot" / "models" / "deeplab_v3.tflite"
    monkeypatch.setattr(demo_video, "DEFAULT_MODEL_PATH", model_path)

    def fake_download(url: str, filename: Path) -> None:
        assert url == demo_video.MODEL_URL
        Path(filename).write_bytes(b"model")

    monkeypatch.setattr(demo_video, "urlretrieve", fake_download)

    assert demo_video._ensure_model(model_path) == model_path
    assert model_path.read_bytes() == b"model"


def test_missing_input_exits_with_clear_message() -> None:
    result = subprocess.run(
        [sys.executable, "iot/demo_video.py", "--input", "arquivo-inexistente.mp4"],
        cwd=Path.cwd(),
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    assert "arquivo de entrada nao encontrado" in result.stderr


def test_segmentation_failure_uses_full_mask_logs_and_penalizes_confidence(monkeypatch, capsys) -> None:
    def fail_segment(segmenter, frame_rgb, timestamp_ms):
        raise RuntimeError("category_mask ausente")

    monkeypatch.setattr(demo_video, "_segment_frame", fail_segment)
    frame_rgb = np.zeros((6, 8, 3), dtype=np.uint8)

    mask, fallback_used = demo_video._segment_frame_with_fallback(
        object(),
        frame_rgb,
        33,
        "video_frame_000001",
    )
    quality = penalize_quality_for_fallback({
        "cloud_score": 0.0,
        "shadow_score": 0.0,
        "brightness_score": 0.5,
        "blur_score": 0.1,
        "image_quality": "boa",
        "cv_confidence": 0.91,
    })

    assert fallback_used is True
    assert mask.shape == (6, 8)
    assert np.all(mask == 1.0)
    assert quality["image_quality"] == "baixa"
    assert quality["cv_confidence"] <= 0.2

    captured = capsys.readouterr()
    assert "component=segmentation" in captured.err
    assert "video_frame_000001" in captured.err
    assert "RuntimeError" in captured.err
