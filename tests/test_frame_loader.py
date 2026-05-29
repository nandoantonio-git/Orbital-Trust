import os
import pytest
import numpy as np
from iot.frame_loader import load_frames

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "frames")


def test_load_frames_returns_numpy_arrays():
    frames = load_frames(FIXTURE_DIR)
    assert len(frames) == 2
    assert all(isinstance(f, np.ndarray) for f in frames)


def test_load_frames_ignores_non_images():
    frames = load_frames(FIXTURE_DIR)
    # fixture has 2 images + 1 .txt; only images should be returned
    assert len(frames) == 2


def test_load_frames_missing_folder_raises():
    with pytest.raises(FileNotFoundError):
        load_frames("/nonexistent/path/to/frames")
