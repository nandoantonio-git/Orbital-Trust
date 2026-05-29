import cv2
import numpy as np


def compute_change_score(frame_a: np.ndarray, frame_b: np.ndarray) -> float:
    """Return normalized change score in [0.0, 1.0] between two frames.

    Uses mean absolute difference on grayscale frames normalized to [0, 255].
    Identical frames → 0.0; fully inverted frames → 1.0.
    """
    gray_a = cv2.cvtColor(frame_a, cv2.COLOR_BGR2GRAY).astype(np.float32)
    gray_b = cv2.cvtColor(frame_b, cv2.COLOR_BGR2GRAY).astype(np.float32)
    diff = np.abs(gray_a - gray_b)
    score = float(diff.mean() / 255.0)
    return round(min(max(score, 0.0), 1.0), 6)
