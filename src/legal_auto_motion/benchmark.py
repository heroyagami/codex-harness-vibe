from __future__ import annotations

import json
from pathlib import Path


def _load(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def summarize_run(run_dir: Path) -> dict:
    metrics = _load(run_dir / "reports" / "production-metrics.json")
    sequence = _load(run_dir / "reports" / "sequence-review.json")
    completion = _load(run_dir / "completion-report.json")
    provenance = _load(run_dir / "reports" / "scene-provenance.json")
    critiques = []
    revision_calls = 0
    for scene in provenance.get("scenes", []):
        critic = scene.get("critic", {})
        if isinstance(critic.get("total"), int):
            critiques.append(int(critic["total"]))
        revision_calls += int(scene.get("revision_calls", 0) or 0)
    scene_count = int(provenance.get("scene_count", 0) or sequence.get("scene_count", 0) or 0)
    failed = int(metrics.get("summary", {}).get("failed_calls", 0) or 0)
    calls = int(metrics.get("summary", {}).get("calls", 0) or 0)
    repeated_motion_runs = sequence.get("repeated_motion_signature_runs", [])
    repeated_silhouette_runs = sequence.get("repeated_silhouette_runs", [])
    return {
        "run": run_dir.name,
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
    }


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
    return {"version": "benchmark-v2-motion-diversity", "runs": rows, "best": best}


def write_benchmark(run_dirs: list[Path], output: Path) -> dict:
    report = compare_runs(run_dirs)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report
