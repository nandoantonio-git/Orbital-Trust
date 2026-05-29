import os
import uuid
from typing import List

import cv2

from iot.change_detector import compute_change_score
from iot.detector import detect_class
from iot.payload import build_payload
from iot.quality import compute_quality_metrics

_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def run_pipeline(frames_folder: str, area_id: str, source: str) -> List[dict]:
    """Process consecutive frame pairs from a folder and return validated payloads."""
    if not os.path.exists(frames_folder):
        raise FileNotFoundError(f"Folder not found: {frames_folder}")

    entries = sorted(
        f for f in os.listdir(frames_folder)
        if os.path.splitext(f)[1].lower() in _IMAGE_EXTENSIONS
    )

    frames = []
    for filename in entries:
        img = cv2.imread(os.path.join(frames_folder, filename))
        if img is not None:
            frames.append((filename, img))

    payloads = []
    for i in range(len(frames) - 1):
        name_a, frame_a = frames[i]
        name_b, frame_b = frames[i + 1]

        change_score = compute_change_score(frame_a, frame_b)
        detector_result = detect_class(frame_b)
        quality_result = compute_quality_metrics(frame_b)

        payload = build_payload(
            event_id=str(uuid.uuid4()),
            area_id=area_id,
            source=source,
            detector_result=detector_result,
            quality_result=quality_result,
            change_score=change_score,
            frame_reference=f"{name_a}>{name_b}",
        )
        payloads.append(payload)

    return payloads
