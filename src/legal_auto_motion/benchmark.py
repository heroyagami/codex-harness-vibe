from __future__ import annotations

import json
import tomllib
from pathlib import Path


def _load(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _memory_variant(run_dir: Path) -> str:
    config = run_dir / "harness.toml"
    if not config.exists():
        return "unknown"
    try:
        with config.open("rb") as handle:
            data = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError):
        return "unknown"
    memory = data.get("memory", {})
    enabled = bool(memory.get("enabled", True))
    if not enabled:
        return "memory_off"
    policy = str(memory.get("policy", "quality_ranked")).strip() or "quality_ranked"
    return f"memory_on:{policy}"


def summarize_run(run_dir: Path) -> dict:
    metrics = _load(run_dir / "reports" / "production-metrics.json")
    sequence = _load(run_dir / "reports" / "sequence-review.json")
    completion = _load(run_dir / "completion-report.json")
    provenance = _load(run_dir / "reports" / "scene-provenance.json")
    critiques = []
    revision_calls = 0
    attention_failures = 0
    attention_drifts: list[float] = []
    for scene in provenance.get("scenes", []):
        critic = scene.get("critic", {})
        if isinstance(critic.get("total"), int):
            critiques.append(int(critic["total"]))
        revision_calls += int(scene.get("revision_calls", 0) or 0)
    for scene_dir in sorted((run_dir / "scenes").glob("scene-*")):
        visual = _load(scene_dir / "artifacts" / "visual-gate" / "visual-gate.json")
        attention = visual.get("attention_gate", {})
        attention_failures += int(attention.get("representative_failures", 0) or 0)
        if isinstance(attention.get("max_centroid_drift"), (int, float)):
            attention_drifts.append(float(attention["max_centroid_drift"]))
    scene_count = int(provenance.get("scene_count", 0) or sequence.get("scene_count", 0) or 0)
    failed = int(metrics.get("summary", {}).get("failed_calls", 0) or 0)
    calls = int(metrics.get("summary", {}).get("calls", 0) or 0)
    repeated_motion_runs = sequence.get("repeated_motion_signature_runs", [])
    repeated_silhouette_runs = sequence.get("repeated_silhouette_runs", [])
    return {
        "run": run_dir.name,
        "memory_variant": _memory_variant(run_dir),
        "complete": completion.get("status") == "complete",
        "sequence_status": sequence.get("status", "missing"),
        "scene_count": scene_count,
        "model_calls": calls,
        "failed_calls": failed,
        "failure_rate": round(failed / calls, 4) if calls else 0.0,
        "agent_seconds": float(metrics.get("summary", {}).get("duration_seconds", 0.0) or 0.0),
        "estimated_cost_usd": float(metrics.get("summary", {}).get("estimated_cost_usd", 0.0) or 0.0),
        "revision_calls": revision_calls,
        "revision_calls_per_scene": round(revision_calls / scene_count, 4) if scene_count else 0.0,
        "critic_average": round(sum(critiques) / len(critiques), 3) if critiques else None,
        "critic_min": min(critiques) if critiques else None,
        "energy_range": sequence.get("rhythm", {}).get("energy_range"),
        "max_high_density_run": sequence.get("rhythm", {}).get("max_high_density_run"),
        "max_scenes_without_reset": sequence.get("rhythm", {}).get("max_scenes_without_reset"),
        "repeated_motion_signature_runs": len(repeated_motion_runs) if isinstance(repeated_motion_runs, list) else 0,
        "repeated_silhouette_runs": len(repeated_silhouette_runs) if isinstance(repeated_silhouette_runs, list) else 0,
        "attention_failures": attention_failures,
        "max_attention_drift": round(max(attention_drifts), 4) if attention_drifts else None,
    }


def _average(rows: list[dict], key: str) -> float | None:
    values = [float(row[key]) for row in rows if isinstance(row.get(key), (int, float))]
    return round(sum(values) / len(values), 4) if values else None


def memory_ab_summary(rows: list[dict]) -> dict:
    groups: dict[str, list[dict]] = {}
    for row in rows:
        if not row.get("complete"):
            continue
        groups.setdefault(str(row.get("memory_variant", "unknown")), []).append(row)
    variants = {
        name: {
            "runs": len(items),
            "critic_average": _average(items, "critic_average"),
            "revision_calls_per_scene": _average(items, "revision_calls_per_scene"),
            "failure_rate": _average(items, "failure_rate"),
            "estimated_cost_usd": _average(items, "estimated_cost_usd"),
            "repeated_motion_signature_runs": _average(items, "repeated_motion_signature_runs"),
            "attention_failures": _average(items, "attention_failures"),
        }
        for name, items in sorted(groups.items())
    }
    verdict = "insufficient_variants"
    if "memory_off" in variants and any(name.startswith("memory_on:") for name in variants):
        on_name = sorted(name for name in variants if name.startswith("memory_on:"))[0]
        on = variants[on_name]
        off = variants["memory_off"]
        signals = 0
        if on.get("critic_average") is not None and off.get("critic_average") is not None and on["critic_average"] > off["critic_average"]:
            signals += 1
        if on.get("revision_calls_per_scene") is not None and off.get("revision_calls_per_scene") is not None and on["revision_calls_per_scene"] < off["revision_calls_per_scene"]:
            signals += 1
        if on.get("failure_rate") is not None and off.get("failure_rate") is not None and on["failure_rate"] < off["failure_rate"]:
            signals += 1
        verdict = "memory_on_favored" if signals >= 2 else "no_clear_memory_gain"
    return {"variants": variants, "verdict": verdict}


def compare_runs(run_dirs: list[Path]) -> dict:
    rows = [summarize_run(path.resolve()) for path in run_dirs]
    complete_rows = [row for row in rows if row["complete"]]
    best = {}
    if complete_rows:
        critic_rows = [row for row in complete_rows if row["critic_average"] is not None]
        if critic_rows:
            best["highest_critic_average"] = max(critic_rows, key=lambda row: row["critic_average"])["run"]
        best["lowest_revision_rate"] = min(complete_rows, key=lambda row: row["revision_calls_per_scene"])["run"]
        best["lowest_failure_rate"] = min(complete_rows, key=lambda row: row["failure_rate"])["run"]
        best["lowest_estimated_cost"] = min(complete_rows, key=lambda row: row["estimated_cost_usd"])["run"]
        best["lowest_motion_repetition"] = min(complete_rows, key=lambda row: row["repeated_motion_signature_runs"])["run"]
        best["lowest_attention_failures"] = min(complete_rows, key=lambda row: row["attention_failures"])["run"]
    return {
        "version": "benchmark-v3-memory-ab-attention",
        "runs": rows,
        "best": best,
        "memory_ab": memory_ab_summary(rows),
    }


def write_benchmark(run_dirs: list[Path], output: Path) -> dict:
    report = compare_runs(run_dirs)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report
