from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
from pathlib import Path


SAMPLE_RATE = 16000


def classify_mix_levels(*, effect_db: float, voice_db: float) -> str:
    if voice_db < -42.0 and effect_db >= -36.0:
        return "unmasked"
    if effect_db >= voice_db - 8.0:
        return "audible"
    return "masked"


def summarize_mix_classes(classes: list[str], *, duration_seconds: float) -> dict:
    counts = {name: classes.count(name) for name in ("unmasked", "audible", "masked")}
    total = max(1, len(classes))
    minimum_unmasked = max(2, int(duration_seconds / 45.0))
    problems = []
    if counts["masked"] / total >= 0.5:
        problems.append("at least half of sound-effect cues are masked by narration")
    if classes and counts["unmasked"] < minimum_unmasked:
        problems.append(f"only {counts['unmasked']} unmasked cues; expected at least {minimum_unmasked}")
    return {
        "status": "accepted" if classes and not problems else ("not_applicable" if not classes else "rejected"),
        "counts": counts,
        "masked_ratio": round(counts["masked"] / total, 4),
        "minimum_unmasked": minimum_unmasked,
        "problems": problems,
    }


def _ffmpeg() -> str:
    executable = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
    candidate = Path.home() / "bin" / executable
    return str(candidate) if candidate.exists() else (shutil.which(executable) or "ffmpeg")


def _decode(path: Path):
    try:
        import numpy as np
    except ImportError as exc:
        raise RuntimeError("Audio quality gates require numpy when sfx-cues.json is present") from exc
    raw = subprocess.run(
        [_ffmpeg(), "-v", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", str(SAMPLE_RATE), "-f", "s16le", "-"],
        capture_output=True, check=True,
    ).stdout
    return np.frombuffer(raw, dtype=np.int16).astype(np.float64) / 32768.0


def _db_rms(values) -> float:
    if len(values) == 0:
        return -120.0
    import numpy as np
    return 20.0 * math.log10(max(float(np.sqrt(np.mean(values * values))), 1e-7))


def inspect_audio_mix(final_video: Path, narration: Path, cues_path: Path, output: Path) -> dict:
    import numpy as np
    mix = _decode(final_video)
    voice = _decode(narration)
    length = min(len(mix), len(voice))
    mix, voice = mix[:length], voice[:length]
    window = int(0.2 * SAMPLE_RATE)
    residual = np.empty(length)
    for start in range(0, length, window):
        mixed_window = mix[start:start + window]
        voice_window = voice[start:start + window]
        denominator = float(voice_window @ voice_window)
        gain = float(mixed_window @ voice_window) / denominator if denominator > 1e-9 else 0.0
        residual[start:start + window] = mixed_window - max(0.0, min(3.0, gain)) * voice_window
    cues = json.loads(cues_path.read_text(encoding="utf-8"))
    details, classes = [], []
    for cue in cues:
        time_seconds = float(cue.get("time_seconds", cue.get("t", 0.0)))
        start = max(0, int((time_seconds - 0.05) * SAMPLE_RATE))
        end = min(length, int((time_seconds + 0.45) * SAMPLE_RATE))
        effect_db = _db_rms(residual[start:end])
        voice_db = _db_rms(voice[start:end])
        classification = classify_mix_levels(effect_db=effect_db, voice_db=voice_db)
        classes.append(classification)
        details.append({
            "time_seconds": time_seconds, "classification": classification,
            "effect_db": round(effect_db, 2), "voice_db": round(voice_db, 2),
        })
    report = summarize_mix_classes(classes, duration_seconds=length / SAMPLE_RATE)
    report["cues"] = details
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report
