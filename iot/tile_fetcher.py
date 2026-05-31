from datetime import datetime, timedelta
from typing import Optional, Tuple
from urllib.request import urlopen, Request
import ssl
import certifi

import cv2
import numpy as np

from iot.tile_quality import check_tile_integrity

_SSL_CTX = ssl.create_default_context(cafile=certifi.where())


def _date_offsets(max_days: int):
    yield 0
    for d in range(1, max_days + 1):
        yield -d
        yield d


def fetch_best_tile(
    url_template: str,
    base_date: str,
    max_days_offset: int = 3,
) -> Tuple[Optional[np.ndarray], Optional[str]]:
    if not url_template or "{date}" not in url_template:
        print("[tile_fetcher] url_template inválido SKIP")
        return None, None

    base = datetime.strptime(base_date, "%Y-%m-%d")

    for offset in _date_offsets(max_days_offset):
        target = base + timedelta(days=offset)
        date_str = target.strftime("%Y-%m-%d")
        url = url_template.replace("{date}", date_str)

        try:
            req = Request(url)
            with urlopen(req, timeout=30, context=_SSL_CTX) as resp:
                data = resp.read()
        except Exception:
            print(f"[tile_fetcher] {date_str}: download failed SKIP")
            continue

        buf = np.frombuffer(data, dtype=np.uint8)
        frame = cv2.imdecode(buf, cv2.IMREAD_COLOR)
        if frame is None:
            print(f"[tile_fetcher] {date_str}: decode failed SKIP")
            continue

        result = check_tile_integrity(frame)
        if result["passes"]:
            return frame, date_str

        black_ratio = result["black_ratio"]
        print(f"[tile_fetcher] {date_str}: black_ratio={black_ratio:.2f} SKIP")

    return None, None
