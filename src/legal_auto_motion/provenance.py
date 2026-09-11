from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .state import file_hash


PROVENANCE_VERSION = "scene-provenance-v1"


def _json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _hash_optional(path: Path) -> str:
    return file_hash(path) if path.exists() and path.is_file() else ""


def _text_hash(path: Path) -> str:
    if not path.exists():
        return ""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _scene_events(run_dir: Path, scene_id: str) -> list[dict]:
    state = _json(run_dir / "harness-state.json")
    return [
        event for event in state.get("usage", {}).get("events", [])
        if str(event.get("scope", "")) == scene_id
    ]


def build_scene_provenance(scene_dir: Path) -> dict:
    run_dir = scene_dir.parents[1]
    scene_id = scene_dir.name
    contract = _json(scene_dir / "fact-contract.json")
    invocation = _json(scene_dir / ".harness" / "invocation-context.json")
    critique = _json(scene_dir / "artifacts" / "creative-critique.json")
    state = _json(scene_dir / "scene-state.json")
    worker_state = _json(scene_dir / "worker-state.json")
    style_memory = scene_dir / "artifacts" / "style-memory-guidance.md"
    source = scene_dir / "scenes" / "DefaultScene.tsx"
    frame = scene_dir / "frame.md"
    video = scene_dir / f"{scene_id}.mov"
    events = _scene_events(run_dir, scene_id)
    revisions = sum(1 for event in events if str(event.get("role", "")).endswith("revision_worker"))
    models = [
        {
            "role": event.get("role", ""),
            "provider": event.get("provider", ""),
            "model": event.get("model", ""),
            "status": event.get("status", ""),
            "duration_seconds": event.get("duration_seconds", 0.0),
        }
        for event in events
    ]
    manifest = {
        "version": PROVENANCE_VERSION,
        "scene_id": scene_id,
        "director_contract_hash": _hash_optional(scene_dir / "fact-contract.json"),
        "context_policy_version": invocation.get("policy_version", ""),
        "prompt_hash": invocation.get("prompt_sha256", ""),
        "style_memory_hash": _text_hash(style_memory),
        "models": models,
        "revision_calls": revisions,
        "critic": {
            "verdict": critique.get("verdict", ""),
            "total": critique.get("total"),
            "scores": critique.get("scores", {}),
        },
        "scene_state_nodes": sorted(state.get("nodes", {}).keys()),
        "worker_status": worker_state.get("status", ""),
        "contract": {
            key: contract.get(key)
            for key in ("grammar", "section", "subject", "energy", "density", "visual_reset")
            if key in contract
        },
        "outputs": {
            "frame_hash": _hash_optional(frame),
            "source_hash": _hash_optional(source),
            "video_hash": _hash_optional(video),
        },
    }
    output = scene_dir / "artifacts" / "provenance.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def build_run_provenance(run_dir: Path) -> dict:
    scenes = [build_scene_provenance(path) for path in sorted((run_dir / "scenes").glob("scene-*"))]
    report = {
        "version": PROVENANCE_VERSION,
        "scene_count": len(scenes),
        "scenes": scenes,
    }
    reports = run_dir / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    (reports / "scene-provenance.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report
