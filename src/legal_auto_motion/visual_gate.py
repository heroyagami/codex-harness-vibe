from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageChops, ImageStat

from .config import config_for_run
from .video_profile import profile_from_config
from .visual_attention import analyze_attention_frame, summarize_attention


def _ffmpeg() -> str:
    candidate = Path.home() / "bin" / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")
    return str(candidate) if candidate.exists() else (shutil.which("ffmpeg") or "ffmpeg")


def _background_crop(scene_dir: Path, metadata: dict) -> Image.Image:
    background = Image.open(scene_dir / "public" / metadata["background_image"]).convert("RGB")
    anchor = metadata["background_anchor"]
    x = int(float(anchor["x"]) * (metadata["background_width"] - metadata["width"]))
    y = int(float(anchor["y"]) * (metadata["background_height"] - metadata["height"]))
    return background.crop((x, y, x + metadata["width"], y + metadata["height"]))


def _profile(scene_dir: Path, metadata: dict):
    config = config_for_run(scene_dir.parents[1])
    profile = profile_from_config(config.video, config.safe_zone)
    if profile.width != int(metadata["width"]) or profile.height != int(metadata["height"]):
        raise RuntimeError("Configured video profile does not match rendered scene dimensions")
    return profile


def inspect_render(scene_dir: Path) -> dict:
    metadata = json.loads((scene_dir / "scene-metadata.json").read_text(encoding="utf-8"))
    video = scene_dir / metadata["output_file"]
    duration = metadata["duration_in_frames"] / metadata["fps"]
    artifacts = scene_dir / "artifacts" / "visual-gate"
    artifacts.mkdir(parents=True, exist_ok=True)
    profile = _profile(scene_dir, metadata)
    zone = {
        "left": profile.left,
        "right": profile.right,
        "top": profile.top,
        "content_bottom": profile.content_bottom,
        "subtitle_bottom": profile.subtitle_bottom,
        "edge_guard": profile.edge_guard,
    }
    safe_box = (profile.left, profile.top, profile.right, profile.content_bottom)
    safe_width = max(1, profile.right - profile.left)
    safe_height = max(1, profile.content_bottom - profile.top)
    full_background = _background_crop(scene_dir, metadata)
    background = full_background.crop(safe_box)
    samples = []
    attention_samples = []
    unsafe_edge_samples = []
    edge_guard = profile.edge_guard
    scene_width = int(metadata["width"])
    scene_height = int(metadata["height"])
    edge_top = min(100, max(0, profile.top))
    edge_bottom = min(scene_height, max(profile.content_bottom, edge_top + 1))
    for label, ratio in (("early", 0.25), ("mid", 0.50), ("late", 0.75)):
        image_path = artifacts / f"{label}.png"
        subprocess.run(
            [_ffmpeg(), "-y", "-ss", f"{duration * ratio:.3f}", "-i", str(video), "-frames:v", "1", str(image_path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        full_image = Image.open(image_path).convert("RGB")
        review_height = 720
        review_width = max(1, round(scene_width * review_height / scene_height))
        full_image.resize((review_width, review_height), Image.Resampling.LANCZOS).save(
            artifacts / f"{label}-review.jpg", quality=88, optimize=True
        )
        image = full_image.crop(safe_box)
        difference = ImageChops.difference(image, background)
        mean_difference = sum(ImageStat.Stat(difference).mean) / 3
        changed_ratio = sum(1 for value in difference.convert("L").get_flattened_data() if value > 12) / (safe_width * safe_height)
        samples.append(
            {"label": label, "time_seconds": round(duration * ratio, 3), "mean_difference": mean_difference, "changed_ratio": changed_ratio}
        )
        attention = analyze_attention_frame(image, background)
        attention["label"] = label
        attention["time_seconds"] = round(duration * ratio, 3)
        attention_samples.append(attention)
        edge_diff = ImageChops.difference(full_image, full_background).convert("L")
        left = edge_diff.crop((0, edge_top, edge_guard, edge_bottom))
        right = edge_diff.crop((scene_width - edge_guard, edge_top, scene_width, edge_bottom))
        edge_pixels = list(left.get_flattened_data()) + list(right.get_flattened_data())
        edge_changed_ratio = sum(1 for value in edge_pixels if value > 20) / max(1, len(edge_pixels))
        unsafe_edge_samples.append(
            {"label": label, "time_seconds": round(duration * ratio, 3), "changed_ratio": edge_changed_ratio}
        )
    visible_samples = [item for item in samples if item["mean_difference"] >= 3 and item["changed_ratio"] >= 0.01]
    clipped_samples = [item for item in unsafe_edge_samples if item["changed_ratio"] >= 0.025]
    attention = summarize_attention(attention_samples)
    problems = (["representative frames are mostly empty inside the configured content safe zone"] if len(visible_samples) < 2 else [])
    problems += (["foreground content touches or crosses the configured outer edge guard"] if clipped_samples else [])
    problems += attention.get("problems", [])
    report = {
        "scene_id": scene_dir.name,
        "profile": profile.name,
        "canvas": {"width": profile.width, "height": profile.height, "fps": profile.fps},
        "status": "accepted" if not problems else "rejected",
        "safe_zone": zone,
        "samples": samples,
        "attention_gate": attention,
        "unsafe_edge_samples": unsafe_edge_samples,
        "problems": problems,
        "rule": "Representative frames must be visible, primary content must clear the outer edge guard, and visual attention must not fail in two or more representative frames.",
    }
    (artifacts / "visual-gate.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report
