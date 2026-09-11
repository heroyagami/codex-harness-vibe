from __future__ import annotations

from dataclasses import dataclass


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
    if "visual" in lowered_stage or any(token in text for token in ("裁切", "安全区", "safe-zone", "clipped", "subtitle reserve", "主体过小", "遮挡")):
        return ROUTES["visibility"]
    if "motion" in lowered_stage or any(token in text for token in ("freeze", "jitter", "无变化", "运动", "motion", "节奏停滞")):
        return ROUTES["motion"]

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
