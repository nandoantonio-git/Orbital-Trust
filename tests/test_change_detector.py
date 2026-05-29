import numpy as np
from iot.change_detector import compute_change_score


def _solid(value: int, size: int = 64) -> np.ndarray:
    """Return a solid-gray BGR frame (B=G=R=value)."""
    frame = np.full((size, size, 3), value, dtype=np.uint8)
    return frame


def test_identical_frames_return_zero():
    frame = _solid(128)
    assert compute_change_score(frame, frame) == 0.0


def test_identical_copy_returns_zero():
    frame = _solid(50)
    assert compute_change_score(frame, frame.copy()) == 0.0


def test_fully_different_frames_near_one():
    black = _solid(0)
    white = _solid(255)
    score = compute_change_score(black, white)
    assert score >= 0.99


def test_score_in_range():
    a = _solid(0)
    b = _solid(128)
    score = compute_change_score(a, b)
    assert 0.0 <= score <= 1.0


def test_score_symmetry():
    a = _solid(30)
    b = _solid(200)
    assert compute_change_score(a, b) == compute_change_score(b, a)


def test_partial_change():
    size = 64
    a = np.full((size, size, 3), 0, dtype=np.uint8)
    b = a.copy()
    b[:, size // 2 :] = 255  # half the frame changed to white
    score = compute_change_score(a, b)
    assert 0.4 < score < 0.6
