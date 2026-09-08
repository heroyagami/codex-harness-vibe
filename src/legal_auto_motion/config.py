from __future__ import annotations

import copy
import tomllib
from dataclasses import dataclass, field
from pathlib import Path


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
    return HarnessConfig(
        models=routes,
        budget=merged["budget"],
        production=merged["production"],
        source=path,
        memory=merged["memory"],
        assets=merged["assets"],
        quality=merged["quality"],
        alignment=merged["alignment"],
    )


def config_for_run(run_dir: Path, explicit: Path | None = None) -> HarnessConfig:
    candidate = explicit or (run_dir / "harness.toml")
    return load_config(candidate if candidate.exists() else None)
