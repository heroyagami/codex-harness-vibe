from __future__ import annotations

import copy
import tomllib
from dataclasses import dataclass, field
from pathlib import Path


SUPPORTED_RENDER_PROFILE = (1080, 1440, 30)

DEFAULT_CONFIG = {
    "models": {
        "director": {"provider": "codex_text", "model": "", "fallback_model": "", "fallback_provider": "", "command": [], "estimated_cost_usd": 0.0},
        "scene_worker": {"provider": "claude", "model": "", "fallback_model": "", "fallback_provider": "", "command": [], "estimated_cost_usd": 0.0},
        "revision_worker": {"provider": "claude", "model": "", "fallback_model": "", "fallback_provider": "", "command": [], "estimated_cost_usd": 0.0},
        "transition_worker": {"provider": "claude", "model": "", "fallback_model": "", "fallback_provider": "", "command": [], "estimated_cost_usd": 0.0},
        "critic": {"provider": "codex_images", "model": "", "fallback_model": "", "fallback_provider": "", "command": [], "estimated_cost_usd": 0.0},
    },
    "budget": {
        "max_total_cost_usd": 0.0,
        "max_model_calls": 0,
        "max_scene_attempts": 3,
        "max_revision_attempts": 1,
    },
    "production": {
        "scene_concurrency": 3,
        "transition_concurrency": 2,
        "timeout_seconds": 900,
        "require_visual_critic": True,
    },
    "memory": {"enabled": True, "path": "", "max_examples_per_grammar": 3},
    "assets": {"enabled": True, "library_path": "", "max_assets_per_scene": 12},
    "quality": {
        "max_freeze_seconds": 0.8, "check_raster_jitter": True,
        "delivery_render_concurrency": 1, "beat_tolerance_seconds": 0.12,
        "beat_tail_seconds": 0.5, "require_sfx_checks_when_cues_exist": True,
    },
    "alignment": {"require_word_alignment": False, "word_timestamps_file": "word-timestamps.json"},
    "video": {
        "profile": "compact_3_4",
        "width": 1080,
        "height": 1440,
        "fps": 30,
    },
    "safe_zone": {
        "left": 110,
        "right": 970,
        "top": 145,
        "content_bottom": 1000,
        "subtitle_bottom": 1295,
        "edge_guard": 60,
    },
}


@dataclass(frozen=True)
class ModelRoute:
    provider: str
    model: str = ""
    fallback_model: str = ""
    estimated_cost_usd: float = 0.0
    fallback_provider: str = ""
    command: tuple[str, ...] = ()


@dataclass(frozen=True)
class HarnessConfig:
    models: dict[str, ModelRoute] = field(default_factory=dict)
    budget: dict[str, int | float] = field(default_factory=dict)
    production: dict[str, int | bool] = field(default_factory=dict)
    source: Path | None = None
    memory: dict[str, str | int | bool] = field(default_factory=dict)
    assets: dict[str, str | int | bool] = field(default_factory=dict)
    quality: dict[str, str | int | float | bool] = field(default_factory=dict)
    alignment: dict[str, str | bool] = field(default_factory=dict)
    video: dict[str, int | str] = field(default_factory=dict)
    safe_zone: dict[str, int] = field(default_factory=dict)

    def route(self, role: str) -> ModelRoute:
        if role not in self.models:
            raise KeyError(f"Unknown model role: {role}")
        return self.models[role]


def _merge(base: dict, override: dict) -> dict:
    result = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge(result[key], value)
        else:
            result[key] = value
    return result


def _validate_video_and_safe_zone(merged: dict) -> None:
    video = merged["video"]
    safe = merged["safe_zone"]
    for field_name in ("width", "height", "fps"):
        value = video.get(field_name)
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError(f"video.{field_name} must be a positive integer")
    width = int(video["width"])
    height = int(video["height"])
    fps = int(video["fps"])
    if (width, height, fps) != SUPPORTED_RENDER_PROFILE:
        raise ValueError(
            "Current auto-vibe vendor renderer supports only 1080x1440@30; "
            "migrate the vendor/runtime profile before selecting another canvas"
        )
    required = ("left", "right", "top", "content_bottom", "subtitle_bottom", "edge_guard")
    for field_name in required:
        value = safe.get(field_name)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"safe_zone.{field_name} must be a non-negative integer")
    if not 0 <= safe["left"] < safe["right"] <= width:
        raise ValueError("safe_zone left/right must fit inside video.width")
    if not 0 <= safe["top"] < safe["content_bottom"] < safe["subtitle_bottom"] <= height:
        raise ValueError("safe_zone vertical bounds must fit inside video.height")
    if safe["edge_guard"] * 2 >= width:
        raise ValueError("safe_zone.edge_guard is too large for video.width")


def load_config(path: Path | None = None) -> HarnessConfig:
    raw = {}
    if path is not None:
        if not path.exists():
            raise FileNotFoundError(path)
        with path.open("rb") as handle:
            raw = tomllib.load(handle)
    merged = _merge(DEFAULT_CONFIG, raw)
    routes = {
        role: ModelRoute(
            provider=str(value.get("provider", "")).strip(),
            model=str(value.get("model", "")).strip(),
            fallback_model=str(value.get("fallback_model", "")).strip(),
            estimated_cost_usd=float(value.get("estimated_cost_usd", 0.0)),
            fallback_provider=str(value.get("fallback_provider", "")).strip(),
            command=tuple(str(item) for item in value.get("command", [])),
        )
        for role, value in merged["models"].items()
    }
    for role, route in routes.items():
        if not route.provider:
            raise ValueError(f"models.{role}.provider cannot be empty")
        if route.provider == "generic_cli" and not route.command:
            raise ValueError(f"models.{role}.command is required for generic_cli")
    if float(merged["budget"].get("max_total_cost_usd", 0.0)) > 0:
        missing = [role for role, route in routes.items() if route.provider != "disabled" and route.estimated_cost_usd <= 0]
        if missing:
            raise ValueError(f"Cost budget requires estimated_cost_usd for: {', '.join(missing)}")
    _validate_video_and_safe_zone(merged)
    return HarnessConfig(
        models=routes,
        budget=merged["budget"],
        production=merged["production"],
        source=path,
        memory=merged["memory"],
        assets=merged["assets"],
        quality=merged["quality"],
        alignment=merged["alignment"],
        video=merged["video"],
        safe_zone=merged["safe_zone"],
    )


def config_for_run(run_dir: Path, explicit: Path | None = None) -> HarnessConfig:
    candidate = explicit or (run_dir / "harness.toml")
    return load_config(candidate if candidate.exists() else None)
