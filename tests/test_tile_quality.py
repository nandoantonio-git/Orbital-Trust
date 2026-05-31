import numpy as np
from iot.tile_quality import check_tile_integrity, BLACK_RATIO_THRESHOLD


def _solid_bgr(b: int, g: int, r: int, size: int = 100) -> np.ndarray:
    frame = np.zeros((size, size, 3), dtype=np.uint8)
    frame[:, :] = (b, g, r)
    return frame


def _distributed_black_frame(black_pixels: int, size: int = 100) -> np.ndarray:
    frame = np.full((size, size, 3), 128, dtype=np.uint8)
    positions = np.linspace(0, size * size - 1, black_pixels, dtype=int)
    rows, cols = np.unravel_index(positions, (size, size))
    frame[rows, cols] = (0, 0, 0)
    return frame


def _dark_textured_frame(size: int = 100) -> np.ndarray:
    y, x = np.indices((size, size))
    base = ((x * 3 + y * 5) % 35 + 12).astype(np.uint8)
    return np.stack([base, np.roll(base, 3, axis=0), np.roll(base, 5, axis=1)], axis=2)


def test_black_ratio_threshold_constant():
    assert BLACK_RATIO_THRESHOLD == 0.15


def test_all_black_frame_fails():
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    result = check_tile_integrity(frame)
    assert result["passes"] is False
    assert result["black_ratio"] == 1.0


def test_all_colorful_frame_passes():
    frame = _solid_bgr(0, 200, 0)
    result = check_tile_integrity(frame)
    assert result["passes"] is True
    assert result["black_ratio"] == 0.0


def test_fifteen_percent_distributed_black_passes():
    frame = _distributed_black_frame(1500)
    result = check_tile_integrity(frame)
    assert result["passes"] is True
    assert abs(result["black_ratio"] - 0.15) < 1e-6


def test_sixteen_percent_distributed_black_fails():
    frame = _distributed_black_frame(1600)
    result = check_tile_integrity(frame)
    assert result["passes"] is False
    assert abs(result["black_ratio"] - 0.16) < 1e-6
    assert "black_ratio" in result["reason"]


def test_lateral_black_band_fails_at_threshold():
    frame = np.full((100, 100, 3), 128, dtype=np.uint8)
    frame[:, :15] = (0, 0, 0)
    result = check_tile_integrity(frame)
    assert result["passes"] is False
    assert abs(result["black_ratio"] - 0.15) < 1e-6
    assert "largest_black_component" in result["reason"]


def test_diagonal_black_band_fails_below_black_ratio_threshold():
    frame = np.full((100, 100, 3), 128, dtype=np.uint8)
    y, x = np.indices((100, 100))
    frame[np.abs(y - x) <= 7] = (0, 0, 0)
    result = check_tile_integrity(frame)
    assert result["passes"] is False
    assert result["black_ratio"] <= BLACK_RATIO_THRESHOLD
    assert "largest_black_component" in result["reason"]


def test_black_edge_fails_below_component_threshold():
    frame = np.full((100, 100, 3), 128, dtype=np.uint8)
    frame[:5, :] = (0, 0, 0)
    frame[:, :5] = (0, 0, 0)
    result = check_tile_integrity(frame)
    assert result["passes"] is False
    assert result["black_ratio"] < BLACK_RATIO_THRESHOLD
    assert "edge_black_ratio" in result["reason"]


def test_small_natural_shadow_passes_when_tile_has_visual_information():
    frame = _dark_textured_frame()
    frame[45:55, 45:55] = (0, 0, 0)
    result = check_tile_integrity(frame)
    assert result["passes"] is True
    assert result["black_ratio"] == 0.01


def test_dark_frame_with_visual_information_passes():
    frame = _dark_textured_frame()
    result = check_tile_integrity(frame)
    assert result["passes"] is True
    assert result["black_ratio"] == 0.0


def test_dark_blank_frame_fails_as_low_information():
    frame = np.full((100, 100, 3), 11, dtype=np.uint8)
    result = check_tile_integrity(frame)
    assert result["passes"] is False
    assert result["black_ratio"] == 0.0
    assert "low_visual_information" in result["reason"]


def test_reason_ok_when_passes():
    frame = _solid_bgr(0, 200, 0)
    result = check_tile_integrity(frame)
    assert result["reason"] == "ok"


def test_reason_describes_failure():
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    result = check_tile_integrity(frame)
    assert "1.0" in result["reason"] or "1.00" in result["reason"]
    assert "0.15" in result["reason"]


def test_pixel_black_threshold_bgr_10():
    # pixels with all channels == 10 should count as black
    frame = np.full((100, 100, 3), 10, dtype=np.uint8)
    result = check_tile_integrity(frame)
    assert result["passes"] is False
    assert result["black_ratio"] == 1.0


def test_pixel_bgr_11_not_black():
    # pixels with any channel > 10 should NOT count as black
    frame = np.full((100, 100, 3), 11, dtype=np.uint8)
    result = check_tile_integrity(frame)
    assert result["black_ratio"] == 0.0


def test_return_schema():
    frame = np.zeros((50, 50, 3), dtype=np.uint8)
    result = check_tile_integrity(frame)
    assert "passes" in result
    assert "black_ratio" in result
    assert "reason" in result
    assert isinstance(result["passes"], bool)
    assert isinstance(result["black_ratio"], float)
    assert isinstance(result["reason"], str)
