from __future__ import annotations

import copy
import tomllib
from dataclasses import dataclass, field
from pathlib import Path


DEFAULT_CONFIG = {
    "models": {
        "director": {"provider": "codex_text", "model": "", "fallback_model": "", "estimated_cost_usd": 0.0},
        "scene_worker": {"provider": "claude", "model": "", "fallback_model": "", "estimated_cost_usd": 0.0},
        "revision_worker": {"provider": "claude", "model": "", "fallback_model": "", "estimated_cost_usd": 0.0},
        "transition_worker": {"provider": "claude", "model": "", "fallback_model": "", "estimated_cost_usd": 0.0},
        "critic": {"provider": "codex_images", "model": "", "fallback_model": "", "estimated_cost_usd": 0.0},
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
}


@dataclass(frozen=True)
class ModelRoute:
    provider: str
    model: str = ""
    fallback_model: str = ""
    estimated_cost_usd: float = 0.0


@dataclass(frozen=True)
class HarnessConfig:
    models: dict[str, ModelRoute] = field(default_factory=dict)
    budget: dict[str, int | float] = field(default_factory=dict)
    production: dict[str, int | bool] = field(default_factory=dict)
    source: Path | None = None

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
        )
        for role, value in merged["models"].items()
    }
    for role, route in routes.items():
        if not route.provider:
            raise ValueError(f"models.{role}.provider cannot be empty")
    if float(merged["budget"].get("max_total_cost_usd", 0.0)) > 0:
        missing = [role for role, route in routes.items() if route.provider != "disabled" and route.estimated_cost_usd <= 0]
        if missing:
            raise ValueError(f"Cost budget requires estimated_cost_usd for: {', '.join(missing)}")
    return HarnessConfig(routes, merged["budget"], merged["production"], path)


def config_for_run(run_dir: Path, explicit: Path | None = None) -> HarnessConfig:
    candidate = explicit or (run_dir / "harness.toml")
    return load_config(candidate if candidate.exists() else None)
