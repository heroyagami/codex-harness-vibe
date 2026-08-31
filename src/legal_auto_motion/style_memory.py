from __future__ import annotations

import hashlib
import json
from pathlib import Path


DEFAULT_RULES = {
    "avoid": ["连续三个相同轮廓", "大段字幕原文堆叠", "超过五秒没有有效视觉变化"],
    "prefer": ["先让观众看懂人物、物体、动作或关系", "重点随旁白及时出现", "复用原子组件而不是整套布局"],
}


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
        record = {
            "scene_id": scene_id,
            "grammar": grammar,
            "visual_goal": visual_goal,
            "verdict": verdict,
            "scores": scores,
            "problems": problems,
            "revision": revision,
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

    def guidance(self, grammar: str, *, limit: int = 3) -> str:
        rules = json.loads((self.root / "style-rules.json").read_text(encoding="utf-8"))
        good = self._records("good-scenes", grammar, limit)
        bad = self._records("bad-scenes", grammar, limit)
        lines = ["# 可复用风格记忆", "", "## 固定规则"]
        lines.extend(f"- 避免：{value}" for value in rules.get("avoid", []))
        lines.extend(f"- 优先：{value}" for value in rules.get("prefer", []))
        if good:
            lines.extend(["", f"## {grammar} 的有效经验"])
            lines.extend(f"- {item.get('visual_goal', '')}" for item in good)
        if bad:
            lines.extend(["", f"## {grammar} 的失败经验"])
            for item in bad:
                details = "；".join(item.get("problems", []) + item.get("revision", []))
                lines.append(f"- {details or item.get('visual_goal', '')}")
        return "\n".join(lines).strip() + "\n"


def memory_root(value: str, config_source: Path | None = None) -> Path:
    if value:
        candidate = Path(value).expanduser()
        if not candidate.is_absolute() and config_source is not None:
            candidate = config_source.parent / candidate
        return candidate.resolve()
    return (Path.home() / ".codex-harness-vibe" / "memory").resolve()
