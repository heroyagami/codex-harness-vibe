from __future__ import annotations

import json
import os
import shutil
import subprocess
import re
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


def parse_freeze_segments(output: str) -> list[dict]:
    starts = [float(value) for value in re.findall(r"freeze_start:\s*([\d.]+)", output)]
    ends = [float(value) for value in re.findall(r"freeze_end:\s*([\d.]+)", output)]
    durations = [float(value) for value in re.findall(r"freeze_duration:\s*([\d.]+)", output)]
    segments = []
    for index, start in enumerate(starts):
        end = ends[index] if index < len(ends) else None
        duration = durations[index] if index < len(durations) else (end - start if end is not None else None)
        segments.append({
            "start_seconds": round(start, 3),
            "end_seconds": round(end, 3) if end is not None else None,
            "duration_seconds": round(duration, 3) if duration is not None else None,
        })
    return segments


def analyze_jitter_scores(
    scores: list[float], *, fast_motion_threshold: float = 0.08, residual_threshold: float = 0.006,
) -> dict:
    if not scores:
        return {"status": "not_applicable", "reason": "no frame differences"}
    mean = sum(scores) / len(scores)
    if mean >= fast_motion_threshold:
        return {"status": "not_applicable", "mean_change": round(mean, 5), "reason": "fast-motion window"}
    residuals = []
    for index, score in enumerate(scores):
        start, end = max(0, index - 2), min(len(scores), index + 3)
        trend = sum(scores[start:end]) / (end - start)
        residuals.append(abs(score - trend))
    oscillating = sum(1 for value in residuals if value >= residual_threshold)
    rejected = oscillating >= 6
    return {
        "status": "rejected" if rejected else "accepted",
        "mean_change": round(mean, 5),
        "max_residual": round(max(residuals), 5),
        "oscillating_frames": oscillating,
        "problems": ["low-motion region contains persistent frame-to-frame raster oscillation"] if rejected else [],
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


def inspect_motion(scene_dir: Path, *, max_freeze_seconds: float = 0.8, check_raster_jitter: bool = True) -> dict:
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
    freeze_run = subprocess.run(
        [_ffmpeg(), "-hide_banner", "-i", str(video), "-vf", f"freezedetect=n=0.002:d={max_freeze_seconds}", "-f", "null", "-"],
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace", check=False,
    )
    freezes = parse_freeze_segments(freeze_run.stderr)
    duration = float(metadata.get("duration_frames", 0)) / float(metadata.get("fps", 30) or 30)
    for item in freezes:
        if item.get("end_seconds") is None and duration > float(item["start_seconds"]):
            item["end_seconds"] = round(duration, 3)
            item["duration_seconds"] = round(duration - float(item["start_seconds"]), 3)
    long_freezes = [item for item in freezes if (item.get("duration_seconds") or 0) >= max_freeze_seconds]
    report["freeze_check"] = {"status": "rejected" if long_freezes else "accepted", "segments": freezes}
    jitter = {"status": "not_applicable", "reason": "raster jitter check disabled"}
    if check_raster_jitter:
        jitter_dir = artifacts / "jitter-frames"
        jitter_dir.mkdir(parents=True, exist_ok=True)
        for old in jitter_dir.glob("*.jpg"):
            old.unlink()
        subprocess.run(
            [_ffmpeg(), "-y", "-i", str(video), "-t", "2", "-vf", "fps=30,scale=270:360:flags=lanczos", "-q:v", "3", str(jitter_dir / "frame-%03d.jpg")],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True,
        )
        jitter_frames = [Image.open(path).convert("RGB") for path in sorted(jitter_dir.glob("frame-*.jpg"))]
        jitter = analyze_jitter_scores([_change_score(a, b) for a, b in zip(jitter_frames, jitter_frames[1:])])
    report["raster_jitter_check"] = jitter
    if long_freezes:
        report.setdefault("problems", []).append(f"freeze lasts at least {max_freeze_seconds:.1f} seconds")
    if jitter.get("status") == "rejected":
        report.setdefault("problems", []).extend(jitter.get("problems", []))
    if report.get("problems"):
        report["status"] = "rejected"
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
