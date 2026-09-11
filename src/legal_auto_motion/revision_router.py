from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RevisionRoute:
    kind: str
    priority: int
    instruction: str


ROUTES = {
    "fact": RevisionRoute(
        "fact", 100,
        "只修复事实、数字、日期、案号、裁判结论或批准屏幕文案违规；不得改镜头结构和时长。",
    ),
    "timing": RevisionRoute(
        "timing", 90,
        "只修复局部帧范围、语义重点时间锚和节奏时点；不得改变事实和整体视觉命题。",
    ),
    "visibility": RevisionRoute(
        "visibility", 80,
        "只修复裁切、安全区、主体过小、层级遮挡和字幕保留区冲突；尽量保留现有构图概念。",
    ),
    "motion": RevisionRoute(
        "motion", 70,
        "只修复冻结、抖动、长时间无变化、同时运动过多或运动缺乏叙事目的；保留事实与核心构图。",
    ),
    "composition": RevisionRoute(
        "composition", 60,
        "修复视觉主体不清、构图空、信息层级竞争或主体位置单调；不要改事实和时长。",
    ),
    "creative": RevisionRoute(
        "creative", 50,
        "围绕当前 visual_goal 重做视觉表达；优先提高 semantic clarity、visual thesis 和 rhythm，不得新增事实。",
    ),
}


def _text(report: dict) -> str:
    values: list[str] = []
    for key in ("problems", "revision"):
        value = report.get(key, [])
        if isinstance(value, list):
            values.extend(str(item) for item in value)
        elif value:
            values.append(str(value))
    nested = report.get("report")
    if isinstance(nested, dict):
        values.append(_text(nested))
    return " ".join(values).lower()


def choose_revision_route(*, stage: str = "", report: dict | None = None) -> RevisionRoute:
    """Choose the narrowest repair route supported by available evidence."""
    report = report or {}
    lowered_stage = stage.lower()
    text = _text(report)

    if "fact" in lowered_stage or any(token in text for token in ("事实", "数字", "金额", "日期", "案号", "结论", "unsupported visible")):
        return ROUTES["fact"]
    if any(token in lowered_stage for token in ("timing", "beat")) or any(token in text for token in ("timing", "anchor", "时间锚", "帧范围", "too late")):
        return ROUTES["timing"]
    if "motion" in lowered_stage or any(token in text for token in ("freeze", "jitter", "无变化", "运动", "motion", "节奏停滞")):
        return ROUTES["motion"]
    if "visual" in lowered_stage or any(token in text for token in ("裁切", "安全区", "safe-zone", "clipped", "subtitle reserve", "主体过小", "遮挡")):
        return ROUTES["visibility"]

    scores = report.get("scores", {}) if isinstance(report.get("scores", {}), dict) else {}
    if int(scores.get("composition", 2)) <= 1 or int(scores.get("information_density", 2)) <= 1:
        return ROUTES["composition"]
    return ROUTES["creative"]


def revision_prompt(route: RevisionRoute, report_path: str) -> str:
    return (
        f"读取 {report_path}。本次返工类型：{route.kind}。"
        f"{route.instruction}"
        "只处理报告中列出的失败项；完成后运行 pnpm run verify，不要自行渲染。"
    )


def _read(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def discover_revision_route(scene_dir: Path, prompt: str) -> tuple[RevisionRoute, str, dict] | None:
    """Infer the active narrow repair from artifacts already produced by the pipeline.

    This runs at the provider-adapter boundary, so every revision Worker provider
    receives the same routing policy without requiring session reuse or broad
    pipeline rewrites.
    """
    lowered = prompt.lower()
    if not any(marker in lowered for marker in ("revision", "修复", "返工", "重新运行", "creative-critique")):
        return None

    artifacts = scene_dir / "artifacts"
    candidates: list[tuple[str, Path]] = []

    if "creative" in lowered or "creative-critique" in lowered or "视觉表达" in prompt:
        candidates.append(("creative", artifacts / "creative-critique.json"))
    if "动画" in prompt or "motion" in lowered or "freeze" in lowered or "jitter" in lowered:
        candidates.append(("motion", artifacts / "visual-revision-request.json"))
        candidates.append(("motion", artifacts / "motion-gate" / "motion-gate.json"))
    if "可见" in prompt or "安全区" in prompt or "裁切" in prompt or "visual" in lowered:
        candidates.append(("visual", artifacts / "visual-revision-request.json"))
        candidates.append(("visual", artifacts / "visual-gate" / "visual-gate.json"))
    if "timing" in lowered or "beat" in lowered or "帧" in prompt:
        candidates.append(("timing", artifacts / "timing-revision-request.json"))
        candidates.append(("timing", artifacts / "timing-audit.json"))
    if "fact" in lowered or "事实" in prompt or "数字" in prompt:
        candidates.append(("fact", artifacts / "fact-revision-request.json"))
        candidates.append(("fact", artifacts / "fact-audit.json"))

    # Generic revision prompts can mention both fact and timing. Prefer actual
    # rejected evidence, otherwise fall back to the creative critique.
    candidates.extend([
        ("fact", artifacts / "fact-revision-request.json"),
        ("timing", artifacts / "timing-revision-request.json"),
        ("creative", artifacts / "creative-critique.json"),
    ])

    seen: set[Path] = set()
    for stage, path in candidates:
        if path in seen:
            continue
        seen.add(path)
        report = _read(path)
        if not report:
            continue
        route = choose_revision_route(stage=stage, report=report)
        try:
            display = str(path.relative_to(scene_dir))
        except ValueError:
            display = str(path)
        return route, display.replace("\\", "/"), report
    return None
