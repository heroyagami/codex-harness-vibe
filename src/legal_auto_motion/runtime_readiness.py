from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from .video_profile import VideoProfile


def png_dimensions(path: Path) -> tuple[int, int]:
    with path.open("rb") as handle:
        header = handle.read(24)
    if len(header) < 24 or header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
        raise ValueError(f"not a readable PNG: {path}")
    return int.from_bytes(header[16:20], "big"), int.from_bytes(header[20:24], "big")


def analyze_runtime_readiness(
    profile: VideoProfile,
    *,
    background_dimensions: list[tuple[str, int, int]],
    scene_runtime_dynamic: bool,
    transition_runtime_dynamic: bool,
) -> dict:
    blockers: list[str] = []
    for name, width, height in background_dimensions:
        if width < profile.width or height < profile.height:
            blockers.append(
                f"background {name} is {width}x{height}, smaller than canvas {profile.width}x{profile.height}"
            )
    if not scene_runtime_dynamic:
        blockers.append("scene runtime still contains fixed canvas dimensions")
    if not transition_runtime_dynamic:
        blockers.append("transition runtime still contains fixed canvas dimensions")
    return {
        "profile": asdict(profile),
        "status": "ready" if not blockers else "blocked",
        "blockers": blockers,
    }


def repo_runtime_readiness(repo_root: Path, profile: VideoProfile) -> dict:
    repo_root = repo_root.resolve()
    vendor = repo_root / "vendor" / "auto-vibe"
    backgrounds = []
    for name in ("darkbg.png", "lightbg.png"):
        path = vendor / "resources" / "backgrounds" / name
        if not path.exists():
            backgrounds.append((name, 0, 0))
        else:
            width, height = png_dimensions(path)
            backgrounds.append((name, width, height))
    scene_text = (vendor / "prepare-scenes.py").read_text(encoding="utf-8")
    transition_text = (vendor / "prepare-transitions.py").read_text(encoding="utf-8")
    scene_dynamic = "export const WIDTH = 1080" not in scene_text and '"width": 1080' not in scene_text
    transition_dynamic = "export const WIDTH = 1080" not in transition_text and '"width": 1080' not in transition_text
    return analyze_runtime_readiness(
        profile,
        background_dimensions=backgrounds,
        scene_runtime_dynamic=scene_dynamic,
        transition_runtime_dynamic=transition_dynamic,
    )
