from __future__ import annotations

import json
from pathlib import Path

from .config import config_for_run
from .context_policy import build_boundary_context


RENDERED_TRANSITION_INTENTS = {"carry", "flow", "temporal", "settle"}
HARD_CUT_INTENTS = {"hard_cut", "contrast"}


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _transition_reason(intent: str, *, section_changed: bool) -> str:
    if section_changed:
        return "论证章节发生变化，使用硬切明确重置注意力。"
    reasons = {
        "hard_cut": "语义命题已经完整，使用硬切保持短视频节奏。",
        "contrast": "相邻观点形成反转或强对比，使用硬切放大冲突。",
        "carry": "相邻语义直接延续，允许共享前后景运动完成视觉接力。",
        "flow": "因果或流程继续推进，用连续运动维持方向感。",
        "temporal": "时间关系连续推进，用轻量连续转场表达时间流动。",
        "settle": "语义进入收束或缓冲，用低强度连续转场降低能量。",
    }
    return reasons.get(intent, reasons["hard_cut"])


def _rendered_transition(left: dict, right: dict, intent: str) -> dict:
    boundary = float(left["time_range_seconds"][1])
    left_start = float(left["time_range_seconds"][0])
    right_end = float(right["time_range_seconds"][1])
    left_duration = max(0.0, boundary - left_start)
    right_duration = max(0.0, right_end - boundary)
    half_window = min(0.300, left_duration * 0.22, right_duration * 0.22)
    if half_window < 0.050:
        return {
            "type": "hard_cut",
            "reason": "相邻镜头时长不足以安全容纳渲染转场，自动降级为硬切。",
        }
    return {
        "type": "parallax",
        "time_range_seconds": [f"{boundary - half_window:.3f}", f"{boundary + half_window:.3f}"],
        "reason": _transition_reason(intent, section_changed=False),
        "director_intent": intent,
    }


def apply_director_overlays(run_dir: Path, director_plan: Path | None = None) -> dict:
    director_path = director_plan or (run_dir / "director-plan.json")
    director = json.loads(director_path.read_text(encoding="utf-8"))
    plan_path = run_dir / "scene-plan.json"
    contracts_path = run_dir / "fact-contracts.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    contracts = json.loads(contracts_path.read_text(encoding="utf-8"))
    source_scenes = director.get("scenes", [])
    if len(source_scenes) != len(plan.get("scenes", [])):
        raise ValueError("Director overlay scene count does not match scene plan")

    config = config_for_run(run_dir)
    safe_zone = {key: int(value) for key, value in config.safe_zone.items()}
    neighbor_limit = int(config.context.get("max_neighbor_summary_chars", 700))
    for index, source in enumerate(source_scenes):
        scene_id = f"scene-{index + 1:03d}"
        contract = contracts[scene_id]
        contract.update(
            {
                "subject": source.get("subject", source.get("meaning", "")),
                "grammar": source.get("grammar", ""),
                "section": source.get("section", "body"),
                "energy": float(source.get("energy", 0.5)),
                "density": source.get("density", "medium"),
                "visual_reset": bool(source.get("visual_reset", False)),
                "contrast_with_previous": source.get("contrast_with_previous", "medium"),
                "transition_intent": source.get("transition_intent", "hard_cut"),
                "safe_zone": safe_zone,
                "video_profile": config.video.get("profile", "compact_3_4"),
                "boundary_context": build_boundary_context(source_scenes, index, max_chars=neighbor_limit),
            }
        )

    transitions = []
    for index, (left, right) in enumerate(zip(source_scenes, source_scenes[1:])):
        left_plan = plan["scenes"][index]
        right_plan = plan["scenes"][index + 1]
        section_changed = left.get("section") != right.get("section")
        intent = str(right.get("transition_intent", "hard_cut"))
        if section_changed or intent in HARD_CUT_INTENTS or intent not in RENDERED_TRANSITION_INTENTS:
            transitions.append(
                {
                    "type": "hard_cut",
                    "reason": _transition_reason(intent, section_changed=section_changed),
                    "director_intent": intent,
                }
            )
        else:
            transitions.append(_rendered_transition(left_plan, right_plan, intent))

    plan["transitions"] = transitions
    plan["director_overlay_version"] = "director-overlay-v2-context-boundary"
    _write_json(plan_path, plan)
    _write_json(contracts_path, contracts)
    return {
        "scene_count": len(source_scenes),
        "rendered_transition_count": sum(1 for item in transitions if item["type"] != "hard_cut"),
        "hard_cut_count": sum(1 for item in transitions if item["type"] == "hard_cut"),
    }
