from __future__ import annotations

import hashlib
import json
from pathlib import Path


DEFAULT_RULES = {
    "avoid": ["连续三个相同轮廓", "大段字幕原文堆叠", "超过五秒没有有效视觉变化"],
    "prefer": ["先让观众看懂人物、物体、动作或关系", "重点随旁白及时出现", "复用原子组件而不是整套布局"],
}


def _clip(value: str, limit: int) -> str:
    text = str(value).strip()
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


class StyleMemory:
    def __init__(self, root: Path):
        self.root = root.expanduser().resolve()
        (self.root / "good-scenes").mkdir(parents=True, exist_ok=True)
        (self.root / "bad-scenes").mkdir(parents=True, exist_ok=True)
        rules = self.root / "style-rules.json"
        if not rules.exists():
            rules.write_text(json.dumps(DEFAULT_RULES, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def record(
        self, *, scene_id: str, grammar: str, visual_goal: str, verdict: str,
        scores: dict, problems: list[str], revision: list[str], source_run: str = "",
    ) -> Path:
        # Memory intentionally stores critique lessons, never frame.md, source code,
        # prompts, conversation transcripts or complete rendered-scene descriptions.
        record = {
            "scene_id": scene_id,
            "grammar": grammar,
            "visual_goal": _clip(visual_goal, 300),
            "verdict": verdict,
            "scores": scores,
            "problems": [_clip(item, 220) for item in problems[:6]],
            "revision": [_clip(item, 220) for item in revision[:6]],
            "source_run": source_run,
        }
        digest = hashlib.sha256(
            json.dumps(record, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()[:16]
        folder = "good-scenes" if verdict == "pass" else "bad-scenes"
        path = self.root / folder / f"{grammar or 'unknown'}-{digest}.json"
        path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return path

    def _records(self, folder: str, grammar: str, limit: int) -> list[dict]:
        records = []
        for path in sorted((self.root / folder).glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if not grammar or record.get("grammar") == grammar:
                records.append(record)
            if len(records) >= limit:
                break
        return records

    def guidance(self, grammar: str, *, limit: int = 2, max_chars: int = 3500) -> str:
        rules = json.loads((self.root / "style-rules.json").read_text(encoding="utf-8"))
        good = self._records("good-scenes", grammar, limit)
        bad = self._records("bad-scenes", grammar, limit)
        lines = [
            "# 可复用风格记忆",
            "",
            "> 仅提供抽象经验，不包含历史 scene 的完整布局、源码、Prompt 或对话历史。",
            "",
            "## 固定规则",
        ]
        lines.extend(f"- 避免：{_clip(value, 180)}" for value in rules.get("avoid", [])[:8])
        lines.extend(f"- 优先：{_clip(value, 180)}" for value in rules.get("prefer", [])[:8])
        if good:
            lines.extend(["", f"## {grammar} 的有效经验"])
            lines.extend(f"- {_clip(item.get('visual_goal', ''), 220)}" for item in good)
        if bad:
            lines.extend(["", f"## {grammar} 的失败经验"])
            for item in bad:
                details = "；".join(item.get("problems", []) + item.get("revision", []))
                lines.append(f"- {_clip(details or item.get('visual_goal', ''), 300)}")
        text = "\n".join(lines).strip() + "\n"
        return _clip(text, max_chars).rstrip() + "\n"


def memory_root(value: str, config_source: Path | None = None) -> Path:
    if value:
        candidate = Path(value).expanduser()
        if not candidate.is_absolute() and config_source is not None:
            candidate = config_source.parent / candidate
        return candidate.resolve()
    return (Path.home() / ".codex-harness-vibe" / "memory").resolve()
