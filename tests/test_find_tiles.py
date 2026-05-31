import sys
import importlib
from unittest.mock import patch, MagicMock
from typing import List

import cv2
import numpy as np
import pytest

sys.path.insert(0, "/workspace")
import scripts.find_tiles as ft


def _encode_png(frame: np.ndarray) -> bytes:
    _, buf = cv2.imencode(".png", frame)
    return bytes(buf)


def _green_frame(size: int = 32) -> np.ndarray:
    # BGR(0,200,0) → green channel dominance → "vegetacao"
    f = np.zeros((size, size, 3), dtype=np.uint8)
    f[:, :] = (0, 200, 0)
    return f


def _dark_frame(size: int = 32) -> np.ndarray:
    # BGR(20,20,20) → very dark → "queimada"
    return np.full((size, size, 3), 20, dtype=np.uint8)


def _black_frame(size: int = 32) -> np.ndarray:
    return np.zeros((size, size, 3), dtype=np.uint8)


def _fake_urlopen(responses: List[bytes]):
    idx = [0]

    def _open(req, timeout=None, context=None):
        i = idx[0]
        idx[0] += 1
        m = MagicMock()
        m.read.return_value = responses[i]
        m.__enter__ = lambda s: s
        m.__exit__ = MagicMock(return_value=False)
        return m

    return _open


# ── BRAZIL_REGIONS constant ───────────────────────────────────────────────────

def test_brazil_regions_has_mato_grosso():
    assert "mato_grosso" in ft.BRAZIL_REGIONS
    assert ft.BRAZIL_REGIONS["mato_grosso"] == {"row": 73, "col": 88}


def test_brazil_regions_has_pantanal():
    assert "pantanal" in ft.BRAZIL_REGIONS
    assert ft.BRAZIL_REGIONS["pantanal"] == {"row": 76, "col": 87}


def test_brazil_regions_has_para_amazonia():
    assert "para_amazonia" in ft.BRAZIL_REGIONS
    assert ft.BRAZIL_REGIONS["para_amazonia"] == {"row": 67, "col": 91}


def test_brazil_regions_has_sertao_ne():
    assert "sertao_ne" in ft.BRAZIL_REGIONS
    assert ft.BRAZIL_REGIONS["sertao_ne"] == {"row": 68, "col": 99}


# ── find_tile_for_class returns matching tile ─────────────────────────────────

def test_find_tile_returns_match_when_class_found():
    with patch("scripts.find_tiles.urlopen", side_effect=_fake_urlopen([_encode_png(_green_frame())])):
        result = ft.find_tile_for_class("vegetacao", row=73, col=88, start_date="2024-09-01", max_days=1)

    assert result is not None
    assert result["detected_class"] == "vegetacao"
    assert result["class_percentage"] > 0.0
    assert isinstance(result["image_quality"], float)
    assert isinstance(result["url"], str)
    assert isinstance(result["date"], str)


def test_find_tile_returns_none_when_class_mismatch():
    # tile is "vegetacao" but we want "queimada" → should return None
    responses = [_encode_png(_green_frame())] * 5
    with patch("scripts.find_tiles.urlopen", side_effect=_fake_urlopen(responses)):
        result = ft.find_tile_for_class("queimada", row=73, col=88, start_date="2024-09-01", max_days=2)

    assert result is None


def test_find_tile_returns_none_when_all_tiles_black():
    responses = [_encode_png(_black_frame())] * 5
    with patch("scripts.find_tiles.urlopen", side_effect=_fake_urlopen(responses)):
        result = ft.find_tile_for_class("vegetacao", row=73, col=88, start_date="2024-09-01", max_days=2)

    assert result is None


def test_find_tile_result_schema_keys():
    with patch("scripts.find_tiles.urlopen", side_effect=_fake_urlopen([_encode_png(_dark_frame())])):
        result = ft.find_tile_for_class("queimada", row=73, col=88, start_date="2024-09-01", max_days=1)

    assert result is not None
    assert set(result.keys()) == {"url", "date", "detected_class", "class_percentage", "image_quality"}


def test_find_tile_image_quality_is_one_minus_black_ratio():
    frame = _green_frame(size=100)
    # 10% black
    frame[:10, :] = 0

    with patch("scripts.find_tiles.urlopen", side_effect=_fake_urlopen([_encode_png(frame)])):
        result = ft.find_tile_for_class("vegetacao", row=73, col=88, start_date="2024-09-01", max_days=1)

    assert result is not None
    assert abs(result["image_quality"] - 0.90) < 0.01


def test_find_tile_url_contains_row_col_date():
    with patch("scripts.find_tiles.urlopen", side_effect=_fake_urlopen([_encode_png(_green_frame())])):
        result = ft.find_tile_for_class("vegetacao", row=73, col=88, start_date="2024-09-01", max_days=1)

    assert result is not None
    assert "73" in result["url"]
    assert "88" in result["url"]
    assert result["date"] == "2024-09-01"


def test_find_tile_iterates_days_when_first_is_black():
    # day 0: black (fails integrity), day -1: green (matches)
    black = _encode_png(_black_frame())
    green = _encode_png(_green_frame())
    responses = [black, green]  # base date fails, offset -1 passes

    with patch("scripts.find_tiles.urlopen", side_effect=_fake_urlopen(responses)):
        result = ft.find_tile_for_class("vegetacao", row=73, col=88, start_date="2024-09-02", max_days=2)

    assert result is not None
    assert result["date"] == "2024-09-01"
