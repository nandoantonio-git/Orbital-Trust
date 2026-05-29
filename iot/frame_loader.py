import os
from typing import List

import cv2
import numpy as np

_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def load_frames(folder_path: str) -> List[np.ndarray]:
    if not os.path.exists(folder_path):
        raise FileNotFoundError(f"Folder not found: {folder_path}")

    frames: List[np.ndarray] = []
    for filename in sorted(os.listdir(folder_path)):
        ext = os.path.splitext(filename)[1].lower()
        if ext not in _IMAGE_EXTENSIONS:
            continue
        img = cv2.imread(os.path.join(folder_path, filename))
        if img is not None:
            frames.append(img)
    return frames
