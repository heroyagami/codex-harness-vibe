from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from .video_profile import VideoProfile


MAX_BACKGROUND_UPSCALE = 1.10


def png_dimensions(path: Path) -> tuple[int, int]:
    with path.open("rb") as handle:
        header = handle.read(24)
    if len(header) < 24 or header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
        raise ValueError(f"not a readable PNG: {path}")
    return int.from_bytes(header[16:20], "big"), int.from_bytes(header[20:24], "big")


def background_cover_scale(profile: VideoProfile, width: int, height: int) -> float:
    if width <= 0 or height <= 0:
        return float("inf")
    return max(1.0, profile.width / width, profile.height / height)


def analyze_runtime_readiness(
    profile: VideoProfile,
    *,
    background_dimensions: list[tuple[str, int, int]],
    scene_runtime_dynamic: bool,
    transition_runtime_dynamic: bool,
    scene_background_cover: bool = True,
    transition_background_cover: bool = True,
    max_background_upscale: float = MAX_BACKGROUND_UPSCALE,
) -> dict:
    blockers: list[str] = []
    background_metrics: list[dict] = []
    for name, width, height in background_dimensions:
        scale = background_cover_scale(profile, width, height)
        background_metrics.append(
            {
                "name": name,
                "width": width,
                "height": height,
                "cover_scale": None if scale == float("inf") else round(scale, 6),
                "upscale_required": scale > 1.0,
            }
        )
        if scale > max_background_upscale:
            blockers.append(
                f"background {name} requires {scale:.3f}x cover upscale for "
                f"{profile.width}x{profile.height}; maximum allowed is "
                f"{max_background_upscale:.2f}x"
            )
    if not scene_runtime_dynamic:
        blockers.append("scene runtime still contains fixed canvas dimensions")
    if not transition_runtime_dynamic:
        blockers.append("transition runtime still contains fixed canvas dimensions")
    if not scene_background_cover:
        blockers.append("scene runtime does not use cover-scale background geometry")
    if not transition_background_cover:
        blockers.append("transition runtime does not use cover-scale background geometry")
    return {
        "profile": asdict(profile),
        "background_policy": {
            "mode": "native_or_cover_upscale",
            "max_upscale": max_background_upscale,
        },
        "backgrounds": background_metrics,
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
    scene_root = (vendor / "sceneFolder" / "remotion" / "Root.tsx").read_text(encoding="utf-8")
    parallax = (vendor / "transitionFolder" / "scenes" / "ParallaxTransition.tsx").read_text(encoding="utf-8")
    return analyze_runtime_readiness(
        profile,
        background_dimensions=backgrounds,
        scene_runtime_dynamic=scene_dynamic,
        transition_runtime_dynamic=transition_dynamic,
        scene_background_cover="coverBackgroundGeometry" in scene_root,
        transition_background_cover="coverBackgroundGeometry" in parallax,
    )
