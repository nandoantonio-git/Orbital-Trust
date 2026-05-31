import numpy as np

BLACK_RATIO_THRESHOLD = 0.15
BLACK_PIXEL_THRESHOLD = 10
LARGE_BLACK_COMPONENT_THRESHOLD = 0.12
EDGE_BLACK_RATIO_THRESHOLD = 0.30
EDGE_BAND_RATIO = 0.05
LOW_INFORMATION_MEAN_THRESHOLD = 15.0
LOW_INFORMATION_STD_THRESHOLD = 5.0
LOW_INFORMATION_ENTROPY_THRESHOLD = 1.0


def _largest_black_component_ratio(black_mask: np.ndarray) -> float:
    height, width = black_mask.shape
    total_pixels = float(height * width)
    visited = np.zeros_like(black_mask, dtype=bool)
    largest = 0

    for start_y, start_x in np.argwhere(black_mask):
        if visited[start_y, start_x]:
            continue

        size = 0
        stack = [(int(start_y), int(start_x))]
        visited[start_y, start_x] = True

        while stack:
            y, x = stack.pop()
            size += 1

            for next_y in range(max(0, y - 1), min(height, y + 2)):
                for next_x in range(max(0, x - 1), min(width, x + 2)):
                    if visited[next_y, next_x] or not black_mask[next_y, next_x]:
                        continue
                    visited[next_y, next_x] = True
                    stack.append((next_y, next_x))

        largest = max(largest, size)

    return float(largest) / total_pixels


def _edge_black_ratio(black_mask: np.ndarray) -> float:
    height, width = black_mask.shape
    band = max(1, int(min(height, width) * EDGE_BAND_RATIO))
    edge_mask = np.zeros_like(black_mask, dtype=bool)
    edge_mask[:band, :] = True
    edge_mask[-band:, :] = True
    edge_mask[:, :band] = True
    edge_mask[:, -band:] = True
    return float(np.logical_and(black_mask, edge_mask).sum()) / float(edge_mask.sum())


def _visual_entropy(gray: np.ndarray) -> float:
    values = np.clip(gray, 0, 255).astype(np.uint8)
    histogram = np.bincount((values // 16).ravel(), minlength=16).astype(np.float64)
    probabilities = histogram[histogram > 0] / float(values.size)
    return float(-np.sum(probabilities * np.log2(probabilities)))


def _has_low_visual_information(frame: np.ndarray) -> bool:
    gray = frame.astype(np.float32).mean(axis=2)
    mean = float(gray.mean())
    std = float(gray.std())
    entropy = _visual_entropy(gray)
    return (
        mean <= LOW_INFORMATION_MEAN_THRESHOLD
        and std <= LOW_INFORMATION_STD_THRESHOLD
        and entropy <= LOW_INFORMATION_ENTROPY_THRESHOLD
    )


def check_tile_integrity(frame: np.ndarray) -> dict:
    black_mask = np.all(frame <= BLACK_PIXEL_THRESHOLD, axis=2)
    black_ratio = float(black_mask.sum()) / float(black_mask.size)

    if black_ratio > BLACK_RATIO_THRESHOLD:
        return {
            "passes": False,
            "black_ratio": black_ratio,
            "reason": f"black_ratio={black_ratio:.2f} exceeds threshold {BLACK_RATIO_THRESHOLD}",
        }

    largest_component_ratio = _largest_black_component_ratio(black_mask)
    if largest_component_ratio >= LARGE_BLACK_COMPONENT_THRESHOLD:
        return {
            "passes": False,
            "black_ratio": black_ratio,
            "reason": (
                f"largest_black_component={largest_component_ratio:.2f} "
                f"exceeds threshold {LARGE_BLACK_COMPONENT_THRESHOLD}"
            ),
        }

    edge_ratio = _edge_black_ratio(black_mask)
    if edge_ratio >= EDGE_BLACK_RATIO_THRESHOLD:
        return {
            "passes": False,
            "black_ratio": black_ratio,
            "reason": f"edge_black_ratio={edge_ratio:.2f} exceeds threshold {EDGE_BLACK_RATIO_THRESHOLD}",
        }

    if _has_low_visual_information(frame):
        return {
            "passes": False,
            "black_ratio": black_ratio,
            "reason": "low_visual_information detected",
        }

    return {"passes": True, "black_ratio": black_ratio, "reason": "ok"}
