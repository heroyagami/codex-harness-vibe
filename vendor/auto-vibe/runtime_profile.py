from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


DEFAULT_WIDTH = 1080
DEFAULT_HEIGHT = 1440
DEFAULT_FPS = 30
MAX_CANVAS_DIMENSION = 16384


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


def validate_background_coverage(profile: RuntimeProfile, background: dict) -> None:
    width = background.get("width")
    height = background.get("height")
    if not isinstance(width, int) or not isinstance(height, int):
        raise RuntimeProfileError("scene-plan background is missing integer dimensions")
    if width < profile.width or height < profile.height:
        raise RuntimeProfileError(
            f"background {width}x{height} is smaller than runtime canvas "
            f"{profile.width}x{profile.height}"
        )
