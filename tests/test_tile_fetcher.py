from unittest.mock import patch, MagicMock
from typing import List

import cv2
import numpy as np
import pytest

from iot.tile_fetcher import fetch_best_tile


def _frame_to_png_bytes(frame: np.ndarray) -> bytes:
    _, buf = cv2.imencode(".png", frame)
    return bytes(buf)


def _black_frame() -> np.ndarray:
    return np.zeros((10, 10, 3), dtype=np.uint8)


def _color_frame() -> np.ndarray:
    return np.full((10, 10, 3), 200, dtype=np.uint8)


def _fake_urlopen(byte_responses: List[bytes]):
    call_idx = [0]

    def fake_open(req, timeout=None, context=None):
        idx = call_idx[0]
        call_idx[0] += 1
        mock_resp = MagicMock()
        mock_resp.read.return_value = byte_responses[idx]
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        return mock_resp

    return fake_open


def test_returns_frame_from_third_attempt():
    # 2 black tiles then 1 colored → 3rd attempt (offset +1) passes
    black = _frame_to_png_bytes(_black_frame())
    color = _frame_to_png_bytes(_color_frame())
    responses = [black, black, color]

    template = "https://example.com/{date}/tile.jpg"
    base_date = "2024-09-30"

    with patch("iot.tile_fetcher.urlopen", side_effect=_fake_urlopen(responses)):
        frame, date_used = fetch_best_tile(template, base_date)

    assert frame is not None
    assert date_used == "2024-10-01"  # offset +1 is the 3rd attempt


def test_returns_none_none_when_all_dates_fail():
    black = _frame_to_png_bytes(_black_frame())
    responses = [black] * 7

    with patch("iot.tile_fetcher.urlopen", side_effect=_fake_urlopen(responses)):
        frame, date_used = fetch_best_tile("https://example.com/{date}/tile.jpg", "2024-09-30")

    assert frame is None
    assert date_used is None


def test_returns_base_date_when_first_passes():
    color = _frame_to_png_bytes(_color_frame())

    with patch("iot.tile_fetcher.urlopen", side_effect=_fake_urlopen([color])):
        frame, date_used = fetch_best_tile("https://example.com/{date}/tile.jpg", "2024-09-30")

    assert frame is not None
    assert date_used == "2024-09-30"


def test_date_order_is_base_minus_plus():
    # Verify offset order: 0, -1, +1, -2, +2, -3, +3
    visited: list = []
    original_open = _fake_urlopen([_frame_to_png_bytes(_black_frame())] * 7)

    def recording_open(req, **kwargs):
        # req may be a Request object or string; extract URL
        url = req.full_url if hasattr(req, "full_url") else str(req)
        visited.append(url)
        return original_open(req, **kwargs)

    with patch("iot.tile_fetcher.urlopen", side_effect=recording_open):
        fetch_best_tile("https://example.com/{date}/tile.jpg", "2024-09-30", max_days_offset=3)

    assert "2024-09-30" in visited[0]
    assert "2024-09-29" in visited[1]  # -1
    assert "2024-10-01" in visited[2]  # +1
    assert "2024-09-28" in visited[3]  # -2
    assert "2024-10-02" in visited[4]  # +2
    assert "2024-09-27" in visited[5]  # -3
    assert "2024-10-03" in visited[6]  # +3


def test_custom_max_days_offset_limits_attempts():
    black = _frame_to_png_bytes(_black_frame())
    responses = [black, black, black]

    call_count = [0]
    original = _fake_urlopen(responses)

    def counting_open(req, **kwargs):
        call_count[0] += 1
        return original(req, **kwargs)

    with patch("iot.tile_fetcher.urlopen", side_effect=counting_open):
        fetch_best_tile("https://example.com/{date}/tile.jpg", "2024-09-30", max_days_offset=1)

    assert call_count[0] == 3  # base, -1, +1
