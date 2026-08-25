from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageChops, ImageStat


def _ffmpeg() -> str:
    candidate = Path.home() / "bin" / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")
    return str(candidate) if candidate.exists() else (shutil.which("ffmpeg") or "ffmpeg")


def _background_crop(scene_dir: Path, metadata: dict) -> Image.Image:
    background = Image.open(scene_dir / "public" / metadata["background_image"]).convert("RGB")
    anchor = metadata["background_anchor"]
    x = int(float(anchor["x"]) * (metadata["background_width"] - metadata["width"]))
    y = int(float(anchor["y"]) * (metadata["background_height"] - metadata["height"]))
    return background.crop((x, y, x + metadata["width"], y + metadata["height"]))


def inspect_render(scene_dir: Path) -> dict:
    metadata = json.loads((scene_dir / "scene-metadata.json").read_text(encoding="utf-8"))
    video = scene_dir / metadata["output_file"]
    duration = metadata["duration_in_frames"] / metadata["fps"]
    artifacts = scene_dir / "artifacts" / "visual-gate"
    artifacts.mkdir(parents=True, exist_ok=True)
    background = _background_crop(scene_dir, metadata).crop((110, 145, 970, 1000))
    samples = []
    unsafe_edge_samples = []
    for label, ratio in (("early", 0.25), ("mid", 0.50), ("late", 0.75)):
        image_path = artifacts / f"{label}.png"
        subprocess.run(
            [_ffmpeg(), "-y", "-ss", f"{duration * ratio:.3f}", "-i", str(video), "-frames:v", "1", str(image_path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        full_image = Image.open(image_path).convert("RGB")
        full_image.resize((540, 720), Image.Resampling.LANCZOS).save(
            artifacts / f"{label}-review.jpg", quality=88, optimize=True
        )
        image = full_image.crop((110, 145, 970, 1000))
        difference = ImageChops.difference(image, background)
        mean_difference = sum(ImageStat.Stat(difference).mean) / 3
        changed_ratio = sum(1 for value in difference.convert("L").get_flattened_data() if value > 12) / (920 * 900)
        samples.append(
            {"label": label, "time_seconds": round(duration * ratio, 3), "mean_difference": mean_difference, "changed_ratio": changed_ratio}
        )
        # Primary content must not run into the physical left/right edge.  This
        # catches oversized typography that is technically rendered but clipped
        # outside the vertical-video canvas (a failure seen in scene-008).
        full_background = _background_crop(scene_dir, metadata)
        edge_diff = ImageChops.difference(full_image, full_background).convert("L")
        left = edge_diff.crop((0, 100, 60, 1000))
        right = edge_diff.crop((1020, 100, 1080, 1000))
        edge_pixels = list(left.get_flattened_data()) + list(right.get_flattened_data())
        edge_changed_ratio = sum(1 for value in edge_pixels if value > 20) / len(edge_pixels)
        unsafe_edge_samples.append(
            {"label": label, "time_seconds": round(duration * ratio, 3), "changed_ratio": edge_changed_ratio}
        )
    visible_samples = [item for item in samples if item["mean_difference"] >= 3 and item["changed_ratio"] >= 0.01]
    clipped_samples = [item for item in unsafe_edge_samples if item["changed_ratio"] >= 0.025]
    report = {
        "scene_id": scene_dir.name,
        "status": "accepted" if len(visible_samples) >= 2 and not clipped_samples else "rejected",
        "samples": samples,
        "unsafe_edge_samples": unsafe_edge_samples,
        "problems": (["representative frames are mostly empty"] if len(visible_samples) < 2 else [])
        + (["foreground content touches or crosses the left/right canvas edge"] if clipped_samples else []),
        "rule": "At least two representative frames must be visible and primary content must stay clear of the outer 60px edges.",
    }
    (artifacts / "visual-gate.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report
