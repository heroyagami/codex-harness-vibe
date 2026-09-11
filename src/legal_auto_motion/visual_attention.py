from __future__ import annotations

from PIL import Image, ImageChops, ImageStat


ATTENTION_GATE_VERSION = "visual-attention-v1"


def _foreground_mask(frame: Image.Image, background: Image.Image, *, threshold: int = 24) -> Image.Image:
    sized = background.convert("RGB").resize(frame.size)
    diff = ImageChops.difference(frame.convert("RGB"), sized).convert("L")
    return diff.point(lambda value: 255 if value >= threshold else 0)


def analyze_attention_frame(frame: Image.Image, background: Image.Image) -> dict:
    """Estimate coarse visual attention without a learned vision model.

    The foreground mask is measured relative to the known scene background.
    This is intentionally conservative: it only rejects obvious cases where
    meaningful foreground content is overwhelmingly pushed to the outer edge.
    """
    mask = _foreground_mask(frame, background)
    width, height = mask.size
    pixels = mask.load()
    points: list[tuple[int, int]] = []
    for y in range(height):
        for x in range(width):
            if pixels[x, y] > 0:
                points.append((x, y))

    total_pixels = max(1, width * height)
    foreground_ratio = len(points) / total_pixels
    if not points:
        return {
            "status": "rejected",
            "foreground_ratio": 0.0,
            "centroid": None,
            "edge_mass_ratio": 1.0,
            "spread_ratio": 0.0,
            "problems": ["no measurable foreground attention target"],
        }

    cx = sum(x for x, _ in points) / len(points)
    cy = sum(y for _, y in points) / len(points)
    min_x = min(x for x, _ in points)
    max_x = max(x for x, _ in points)
    min_y = min(y for _, y in points)
    max_y = max(y for _, y in points)
    spread_ratio = ((max_x - min_x + 1) * (max_y - min_y + 1)) / total_pixels

    margin_x = max(1, round(width * 0.14))
    margin_y = max(1, round(height * 0.12))
    edge_points = sum(
        1
        for x, y in points
        if x < margin_x or x >= width - margin_x or y < margin_y or y >= height - margin_y
    )
    edge_mass_ratio = edge_points / len(points)
    centroid_x = cx / max(1, width - 1)
    centroid_y = cy / max(1, height - 1)

    problems: list[str] = []
    if foreground_ratio < 0.008:
        problems.append("foreground attention target is too small")
    if edge_mass_ratio >= 0.72 and (centroid_x < 0.20 or centroid_x > 0.80 or centroid_y < 0.16 or centroid_y > 0.84):
        problems.append("foreground attention is overwhelmingly concentrated near an outer edge")

    return {
        "status": "accepted" if not problems else "rejected",
        "foreground_ratio": round(foreground_ratio, 5),
        "centroid": {"x": round(centroid_x, 4), "y": round(centroid_y, 4)},
        "edge_mass_ratio": round(edge_mass_ratio, 5),
        "spread_ratio": round(spread_ratio, 5),
        "problems": problems,
    }


def summarize_attention(samples: list[dict]) -> dict:
    valid = [sample for sample in samples if sample.get("centroid")]
    rejected = [sample for sample in samples if sample.get("status") == "rejected"]
    drift = 0.0
    if len(valid) >= 2:
        centers = [sample["centroid"] for sample in valid]
        drift = max(
            abs(a["x"] - b["x"]) + abs(a["y"] - b["y"])
            for a, b in zip(centers, centers[1:])
        )
    problems: list[str] = []
    if len(rejected) >= 2:
        problems.append("visual attention fails in at least two representative frames")
    return {
        "version": ATTENTION_GATE_VERSION,
        "status": "rejected" if problems else "accepted",
        "representative_failures": len(rejected),
        "max_centroid_drift": round(drift, 4),
        "samples": samples,
        "problems": problems,
    }
