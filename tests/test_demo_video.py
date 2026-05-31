import subprocess
import sys
from pathlib import Path

import iot.demo_video as demo_video


def test_demo_video_uses_tasks_api_without_solutions() -> None:
    source = Path("iot/demo_video.py").read_text(encoding="utf-8")
    forbidden_api = "mp" + ".solutions" + ".selfie" + "_segmentation"

    assert forbidden_api not in source
    assert "ImageSegmenter" in source
    assert "BaseOptions" in source
    assert "RunningMode" in source


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
    assert "arquivo de entrada não encontrado" in result.stderr
