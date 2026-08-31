from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageStat


def _ffmpeg() -> str:
    candidate = Path.home() / "bin" / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")
    return str(candidate) if candidate.exists() else (shutil.which("ffmpeg") or "ffmpeg")


def analyze_motion_scores(scores: list[float], *, sample_interval: float, threshold: float = 0.012) -> dict:
    longest = current = meaningful = 0
    for score in scores:
        if score >= threshold:
            meaningful += 1
            current = 0
        else:
            current += 1
            longest = max(longest, current)
    max_idle = round(longest * sample_interval, 3)
    problems = []
    if max_idle >= 5.0:
        problems.append("visual remains effectively unchanged for at least five seconds")
    if scores and meaningful == 0:
        problems.append("sampled frames contain no meaningful visual change")
    return {
        "status": "accepted" if not problems else "rejected",
        "sample_interval_seconds": sample_interval,
        "meaningful_changes": meaningful,
        "max_idle_seconds": max_idle,
        "change_scores": [round(value, 5) for value in scores],
        "problems": problems,
    }


def _change_score(left: Image.Image, right: Image.Image) -> float:
    a = left.convert("L").resize((96, 128))
    b = right.convert("L").resize((96, 128))
    return float(ImageStat.Stat(ImageChops.difference(a, b)).mean[0]) / 255.0


def _contact_sheet(frames: list[Image.Image], output: Path) -> None:
    if not frames:
        return
    width, height, columns = 180, 240, 4
    rows = (len(frames) + columns - 1) // columns
    sheet = Image.new("RGB", (width * columns, (height + 24) * rows), "#101114")
    draw = ImageDraw.Draw(sheet)
    for index, frame in enumerate(frames):
        x = (index % columns) * width
        y = (index // columns) * (height + 24)
        thumb = frame.copy()
        thumb.thumbnail((width, height), Image.Resampling.LANCZOS)
        sheet.paste(thumb, (x + (width - thumb.width) // 2, y))
        draw.text((x + 6, y + height + 3), f"t={index * 0.5:.1f}s", fill="white")
    sheet.save(output, quality=90)


def inspect_motion(scene_dir: Path) -> dict:
    metadata = json.loads((scene_dir / "scene-metadata.json").read_text(encoding="utf-8"))
    video = scene_dir / metadata["output_file"]
    artifacts = scene_dir / "artifacts" / "motion-gate"
    frames_dir = artifacts / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    for old in frames_dir.glob("*.jpg"):
        old.unlink()
    subprocess.run(
        [_ffmpeg(), "-y", "-i", str(video), "-vf", "fps=2,scale=270:360:flags=lanczos", "-q:v", "3", str(frames_dir / "frame-%03d.jpg")],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True,
    )
    frames = [Image.open(path).convert("RGB") for path in sorted(frames_dir.glob("frame-*.jpg"))]
    report = analyze_motion_scores(
        [_change_score(left, right) for left, right in zip(frames, frames[1:])], sample_interval=0.5
    )
    report.update({"scene_id": scene_dir.name, "sample_count": len(frames)})
    strip = artifacts / "motion-contact-sheet.jpg"
    _contact_sheet(frames, strip)
    review_clip = artifacts / "motion-review.mp4"
    subprocess.run(
        [_ffmpeg(), "-y", "-i", str(video), "-an", "-vf", "scale=540:720:flags=lanczos", "-c:v", "libx264", "-preset", "veryfast", "-crf", "28", str(review_clip)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True,
    )
    report.update({"contact_sheet": str(strip), "review_clip": str(review_clip)})
    (artifacts / "motion-gate.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report
