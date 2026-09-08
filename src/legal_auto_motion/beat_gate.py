from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw


def _anchor_candidates(words: list[dict], anchor: str) -> list[float]:
    characters: list[tuple[str, float]] = []
    for word in words:
        text = str(word.get("text", ""))
        start = float(word.get("start", 0.0))
        characters.extend((character, start) for character in text)
    full_text = "".join(character for character, _ in characters)
    candidates = []
    position = full_text.find(anchor)
    while position >= 0:
        candidates.append(characters[position][1])
        position = full_text.find(anchor, position + 1)
    return candidates


def validate_beats(
    beats: list[dict], words: list[dict], *, scene_start: float, scene_end: float,
    tolerance: float = 0.12, tail_seconds: float = 0.5,
) -> dict:
    results = []
    problems = []
    for beat in beats:
        time_seconds = float(beat["time_seconds"])
        anchor = str(beat.get("anchor", "")).strip()
        candidates = _anchor_candidates(words, anchor) if anchor else []
        if not candidates:
            problem = f"anchor not found in aligned words: {anchor or '(empty)'}"
            problems.append(problem)
            results.append({**beat, "status": "rejected", "problem": problem})
            continue
        aligned = min(candidates, key=lambda value: abs(value - time_seconds))
        delta = time_seconds - aligned
        tail = scene_end - time_seconds
        beat_problems = []
        if abs(delta) > tolerance:
            beat_problems.append(f"anchor delta {delta:+.3f}s exceeds {tolerance:.3f}s")
        if time_seconds < scene_start or time_seconds >= scene_end:
            beat_problems.append("beat is outside its scene")
        if tail < tail_seconds:
            beat_problems.append(f"beat has only {tail:.3f}s before scene end")
        problems.extend(beat_problems)
        results.append({
            **beat,
            "status": "accepted" if not beat_problems else "rejected",
            "aligned_start_seconds": round(aligned, 3),
            "delta_seconds": round(delta, 3),
            "tail_seconds": round(tail, 3),
            "problems": beat_problems,
        })
    return {"status": "accepted" if beats and not problems else "rejected", "beats": results, "problems": problems}


def load_aligned_words(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data.get("words"), list):
        return data["words"]
    words = []
    for sentence in data.get("sentences", []):
        words.extend(sentence.get("words", []))
    return words


def render_beat_evidence(video: Path, report: dict, output_dir: Path, *, fps: int = 30) -> Path | None:
    accepted = [beat for beat in report.get("beats", []) if beat.get("status") == "accepted"]
    if not accepted:
        return None
    output_dir.mkdir(parents=True, exist_ok=True)
    executable = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
    ffmpeg = shutil.which(executable) or str(Path.home() / "bin" / executable)
    frames: list[tuple[Image.Image, str]] = []
    scene_start = float(report.get("scene_start_seconds", 0.0))
    for beat_index, beat in enumerate(accepted):
        center = float(beat["time_seconds"]) - scene_start
        for label, absolute_time in (("before", center - 1 / fps), ("anchor", center), ("after", center + 1 / fps)):
            path = output_dir / f"beat-{beat_index + 1:02d}-{label}.jpg"
            subprocess.run(
                [ffmpeg, "-y", "-ss", f"{max(0.0, absolute_time):.4f}", "-i", str(video), "-frames:v", "1", "-vf", "scale=270:360:flags=lanczos", "-q:v", "2", str(path)],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True,
            )
            frames.append((Image.open(path).convert("RGB"), f"{beat.get('anchor', '')} {label}"))
    width, height = 270, 390
    sheet = Image.new("RGB", (width * 3, height * len(accepted)), "#101114")
    draw = ImageDraw.Draw(sheet)
    for index, (frame, label) in enumerate(frames):
        x, y = (index % 3) * width, (index // 3) * height
        sheet.paste(frame, (x, y))
        draw.text((x + 8, y + 364), label, fill="white")
    output = output_dir / "beat-anchor-contact-sheet.jpg"
    sheet.save(output, quality=90)
    return output
