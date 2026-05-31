#!/usr/bin/env python3
"""Find MODIS tiles via GIBS that match a target environmental class in Brazilian regions."""
import argparse
import json
import ssl
import sys
from datetime import datetime, timedelta
from typing import Optional
from urllib.request import Request, urlopen

import certifi
import cv2
import numpy as np

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))

from iot.detector import detect_class
from iot.tile_quality import check_tile_integrity

_SSL_CTX = ssl.create_default_context(cafile=certifi.where())

BRAZIL_REGIONS: dict = {
    "mato_grosso":  {"row": 73, "col": 88},
    "pantanal":     {"row": 76, "col": 87},
    "para_amazonia": {"row": 67, "col": 91},
    "sertao_ne":    {"row": 68, "col": 99},
}

_GIBS_TEMPLATE = (
    "https://gibs.earthdata.nasa.gov/wmts/epsg4326/best"
    "/MODIS_Terra_CorrectedReflectance_TrueColor/default"
    "/{date}/250m/6/{row}/{col}.jpg"
)


def _date_offsets(max_days: int):
    yield 0
    for d in range(1, max_days + 1):
        yield -d
        yield d


def _build_url(row: int, col: int, date: str) -> str:
    return _GIBS_TEMPLATE.format(date=date, row=row, col=col)


def find_tile_for_class(
    target_class: str,
    row: int,
    col: int,
    start_date: str,
    max_days: int = 90,
) -> Optional[dict]:
    base = datetime.strptime(start_date, "%Y-%m-%d")

    for offset in _date_offsets(max_days):
        candidate = base + timedelta(days=offset)
        date_str = candidate.strftime("%Y-%m-%d")
        url = _build_url(row, col, date_str)

        try:
            req = Request(url)
            with urlopen(req, timeout=30, context=_SSL_CTX) as resp:
                data = resp.read()
        except Exception:
            continue

        buf = np.frombuffer(data, dtype=np.uint8)
        frame = cv2.imdecode(buf, cv2.IMREAD_COLOR)
        if frame is None:
            continue

        integrity = check_tile_integrity(frame)
        if not integrity["passes"]:
            continue

        cls_result = detect_class(frame)
        if cls_result["detected_class"] != target_class:
            continue

        return {
            "url": url,
            "date": date_str,
            "detected_class": cls_result["detected_class"],
            "class_percentage": float(cls_result["class_percentage"]),
            "image_quality": round(1.0 - integrity["black_ratio"], 4),
        }

    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Find MODIS tile matching a class in Brazil")
    parser.add_argument("--class", dest="target_class", required=True)
    parser.add_argument("--region", required=True, choices=list(BRAZIL_REGIONS))
    parser.add_argument("--start", required=True, help="start date YYYY-MM-DD")
    parser.add_argument("--max-days", type=int, default=90)
    args = parser.parse_args()

    region = BRAZIL_REGIONS[args.region]
    result = find_tile_for_class(
        target_class=args.target_class,
        row=region["row"],
        col=region["col"],
        start_date=args.start,
        max_days=args.max_days,
    )

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
