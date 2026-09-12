from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


DEFAULT_WIDTH = 1080
DEFAULT_HEIGHT = 1440
DEFAULT_FPS = 30
MAX_CANVAS_DIMENSION = 16384
MAX_BACKGROUND_UPSCALE = 1.10


class RuntimeProfileError(ValueError):
    pass


@dataclass(frozen=True)
class RuntimeProfile:
    width: int
    height: int
    fps: int

    @property
    def name(self) -> str:
        return f"{self.width}x{self.height}@{self.fps}"


@dataclass(frozen=True)
class BackgroundCoverGeometry:
    scale: float
    rendered_width: float
    rendered_height: float
    overflow_x: float
    overflow_y: float


def _positive_int(value, *, field: str, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0 or value > maximum:
        raise RuntimeProfileError(
            f"runtime_profile.{field} must be an integer from 1 to {maximum}"
        )
    return value


def read_runtime_profile(scene_plan_path: str | Path) -> RuntimeProfile:
    """Read the canvas contract from a scene-plan JSON file.

    Existing plans remain backward compatible: when ``runtime_profile`` is
    absent, the purchased renderer's production profile (1080x1440@30) is
    used. New plans may declare width/height/fps explicitly so downstream
    scene and transition workspaces no longer own canvas constants.

    This parser only transports the profile. It does not declare a renderer
    profile production-ready; higher-level readiness/config gates remain
    responsible for that decision.
    """

    path = Path(scene_plan_path).resolve()
    if not path.is_file():
        raise RuntimeProfileError(f"Scene plan not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeProfileError(f"{path}: invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise RuntimeProfileError(f"{path}: expected a JSON object")

    raw = data.get("runtime_profile")
    if raw is None:
        width = DEFAULT_WIDTH
        height = DEFAULT_HEIGHT
        fps = data.get("fps", DEFAULT_FPS)
    else:
        if not isinstance(raw, dict):
            raise RuntimeProfileError(f"{path}: runtime_profile must be an object")
        unknown = sorted(set(raw) - {"width", "height", "fps"})
        if unknown:
            raise RuntimeProfileError(
                f"{path}: runtime_profile has unknown field(s): {', '.join(unknown)}"
            )
        missing = [field for field in ("width", "height", "fps") if field not in raw]
        if missing:
            raise RuntimeProfileError(
                f"{path}: runtime_profile missing field(s): {', '.join(missing)}"
            )
        width = raw["width"]
        height = raw["height"]
        fps = raw["fps"]
        if "fps" in data and data["fps"] != fps:
            raise RuntimeProfileError(
                f"{path}: top-level fps must match runtime_profile.fps"
            )

    return RuntimeProfile(
        width=_positive_int(width, field="width", maximum=MAX_CANVAS_DIMENSION),
        height=_positive_int(height, field="height", maximum=MAX_CANVAS_DIMENSION),
        fps=_positive_int(fps, field="fps", maximum=240),
    )


def background_cover_geometry(
    profile: RuntimeProfile, *, background_width: int, background_height: int
) -> BackgroundCoverGeometry:
    if (
        isinstance(background_width, bool)
        or isinstance(background_height, bool)
        or not isinstance(background_width, int)
        or not isinstance(background_height, int)
        or background_width <= 0
        or background_height <= 0
    ):
        raise RuntimeProfileError("scene-plan background is missing positive integer dimensions")
    scale = max(profile.width / background_width, profile.height / background_height)
    rendered_width = background_width * scale
    rendered_height = background_height * scale
    return BackgroundCoverGeometry(
        scale=scale,
        rendered_width=rendered_width,
        rendered_height=rendered_height,
        overflow_x=max(0.0, rendered_width - profile.width),
        overflow_y=max(0.0, rendered_height - profile.height),
    )


def validate_background_coverage(profile: RuntimeProfile, background: dict) -> BackgroundCoverGeometry:
    """Validate that a shared background can safely cover the runtime canvas.

    The renderer uses CSS-style cover geometry. Small upscales are allowed so
    legacy 1480x1840 texture backgrounds can cover the 1080x1920 migration
    target without inventing a second asset set. Excessive upscaling remains
    fail-closed because it would visibly soften the shared texture and make
    transition crops inconsistent.
    """

    geometry = background_cover_geometry(
        profile,
        background_width=background.get("width"),
        background_height=background.get("height"),
    )
    if geometry.scale > MAX_BACKGROUND_UPSCALE + 1e-9:
        raise RuntimeProfileError(
            f"background {background['width']}x{background['height']} requires "
            f"{geometry.scale:.3f}x upscale to cover runtime canvas "
            f"{profile.width}x{profile.height}; maximum allowed is "
            f"{MAX_BACKGROUND_UPSCALE:.2f}x"
        )
    return geometry
