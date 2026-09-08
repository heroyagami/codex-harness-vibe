from __future__ import annotations

import hashlib
import json
from pathlib import Path


CONTEXT_POLICY_VERSION = "scene-context-isolation-v1"
FORBIDDEN_HISTORY_ARTIFACTS = (
    "other scene prompts",
    "other scene frame.md",
    "other scene source code",
    "other worker conversation history",
    "full-run generation logs",
)


def _clip(text: str, limit: int) -> str:
    text = str(text).strip()
    if limit <= 0 or len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


def neighbor_summary(scene: dict, *, max_chars: int = 700) -> dict:
    """Return a compact semantic boundary summary, never raw scene-generation history."""
    summary = {
        "section": str(scene.get("section", "body")),
        "subject": str(scene.get("subject", scene.get("meaning", ""))),
        "visual_goal": str(scene.get("visual_goal", "")),
        "grammar": str(scene.get("grammar", "")),
        "energy": float(scene.get("energy", 0.5)),
        "density": str(scene.get("density", "medium")),
        "visual_reset": bool(scene.get("visual_reset", False)),
        "transition_intent": str(scene.get("transition_intent", "hard_cut")),
    }
    encoded = json.dumps(summary, ensure_ascii=False, separators=(",", ":"))
    if len(encoded) <= max_chars:
        return summary
    summary["visual_goal"] = _clip(summary["visual_goal"], max(80, max_chars // 3))
    summary["subject"] = _clip(summary["subject"], max(40, max_chars // 6))
    return summary


def build_boundary_context(scenes: list[dict], index: int, *, max_chars: int = 700) -> dict:
    return {
        "previous": neighbor_summary(scenes[index - 1], max_chars=max_chars) if index > 0 else None,
        "next": neighbor_summary(scenes[index + 1], max_chars=max_chars) if index + 1 < len(scenes) else None,
    }


def context_manifest(
    *, scene_id: str, boundary_context: dict, style_memory_chars: int,
    max_prompt_chars: int, max_style_memory_chars: int,
) -> dict:
    payload = {
        "version": CONTEXT_POLICY_VERSION,
        "scene_id": scene_id,
        "isolation": "fresh_process_no_history_inheritance",
        "allowed_inputs": [
            "current director contract",
            "current subtitles and fact contract",
            "brand/design system",
            "compact previous/next boundary summaries",
            "bounded style memory guidance",
            "authorized local asset catalog",
        ],
        "forbidden_inputs": list(FORBIDDEN_HISTORY_ARTIFACTS),
        "boundary_context": boundary_context,
        "budgets": {
            "max_prompt_chars": int(max_prompt_chars),
            "max_style_memory_chars": int(max_style_memory_chars),
            "actual_style_memory_chars": int(style_memory_chars),
        },
    }
    payload["manifest_hash"] = hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return payload


def policy_prompt(manifest: dict) -> str:
    previous = manifest.get("boundary_context", {}).get("previous")
    following = manifest.get("boundary_context", {}).get("next")
    return (
        "\n\n# Scene Context Isolation Contract\n\n"
        f"- Policy: {manifest.get('version')}\n"
        "- 当前任务必须在独立、无历史继承的 Worker 上下文中完成。禁止把多个 scene 放进同一个长会话连续生成。\n"
        "- 只处理当前工作目录和当前 scene 合同；不得读取 ../scenes 下其他 scene 的 prompt、frame.md、源码、artifacts 或 worker-state。\n"
        "- 不得复用其他 Worker 的对话历史、工具历史、完整日志或完整生成结果。重试也必须视为新的独立调用。\n"
        "- Style Memory 只作为少量原则/经验，不得照搬历史完整布局、源码或长文案。\n"
        f"- 前镜头摘要：{json.dumps(previous, ensure_ascii=False) if previous else '无'}\n"
        f"- 后镜头摘要：{json.dumps(following, ensure_ascii=False) if following else '无'}\n"
        "- 跨镜头一致性由 Controller 和上述边界摘要负责；你只负责当前 scene。\n"
    )


def write_manifest(scene_dir: Path, manifest: dict) -> Path:
    output = scene_dir / "artifacts" / "context-manifest.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output
