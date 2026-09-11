from __future__ import annotations

import hashlib
import json
import math
import re
import time
from pathlib import Path


MEMORY_SCHEMA_VERSION = "style-memory-v2-quality-ranked"
DEFAULT_RULES = {
    "avoid": ["连续三个相同轮廓", "大段字幕原文堆叠", "超过五秒没有有效视觉变化"],
    "prefer": ["先让观众看懂人物、物体、动作或关系", "重点随旁白及时出现", "复用原子组件而不是整套布局"],
}


def _clip(value: str, limit: int) -> str:
    text = str(value).strip()
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


def _normalized(value: str) -> str:
    return re.sub(r"\s+", "", str(value).lower())


def _score_total(scores: dict) -> tuple[float, float]:
    values = [float(value) for value in scores.values() if isinstance(value, (int, float))]
    if not values:
        return 0.0, 0.0
    total = sum(values)
    maximum = 2.0 * len(values)
    return total, total / maximum if maximum else 0.0


def _age_decay(recorded_at: float, *, half_life_days: float = 120.0) -> float:
    age_days = max(0.0, (time.time() - float(recorded_at or time.time())) / 86400.0)
    return math.pow(0.5, age_days / half_life_days)


def _lesson_key(grammar: str, visual_goal: str, problems: list[str], revision: list[str]) -> str:
    payload = "|".join([
        _normalized(grammar),
        _normalized(visual_goal),
        *(_normalized(item) for item in problems[:3]),
        *(_normalized(item) for item in revision[:3]),
    ])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:20]


def memory_quality(record: dict) -> float:
    """Score a memory lesson for retrieval, not artistic truth."""
    _, normalized_score = _score_total(dict(record.get("scores", {})))
    problems = [str(value) for value in record.get("problems", []) if str(value).strip()]
    revisions = [str(value) for value in record.get("revision", []) if str(value).strip()]
    decay = _age_decay(float(record.get("recorded_at", time.time())))
    verdict = str(record.get("verdict", "revise"))
    revision_count = record.get("revision_count")

    if verdict == "pass":
        zero_revision_bonus = 0.0
        if isinstance(revision_count, int):
            zero_revision_bonus = 0.16 if revision_count == 0 else max(0.0, 0.12 - revision_count * 0.04)
        specificity = min(0.08, len(str(record.get("visual_goal", ""))) / 800.0)
        raw = 0.68 * normalized_score + zero_revision_bonus + specificity
    else:
        specificity = min(0.34, len(problems) * 0.055 + len(revisions) * 0.065)
        low_score_signal = 0.20 * (1.0 - normalized_score) if record.get("scores") else 0.08
        raw = 0.34 + specificity + low_score_signal
    return round(max(0.0, min(1.0, raw * (0.72 + 0.28 * decay))), 4)


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
        revision_count: int | None = None,
    ) -> Path:
        # Memory intentionally stores critique lessons, never frame.md, source code,
        # prompts, conversation transcripts or complete rendered-scene descriptions.
        now = time.time()
        clipped_problems = [_clip(item, 220) for item in problems[:6]]
        clipped_revision = [_clip(item, 220) for item in revision[:6]]
        record = {
            "schema_version": MEMORY_SCHEMA_VERSION,
            "scene_id": scene_id,
            "grammar": grammar,
            "visual_goal": _clip(visual_goal, 300),
            "verdict": verdict,
            "scores": scores,
            "problems": clipped_problems,
            "revision": clipped_revision,
            "source_run": source_run,
            "recorded_at": now,
            "lesson_key": _lesson_key(grammar, visual_goal, clipped_problems, clipped_revision),
        }
        if revision_count is not None:
            record["revision_count"] = max(0, int(revision_count))
        record["quality_score"] = memory_quality(record)
        folder = "good-scenes" if verdict == "pass" else "bad-scenes"
        destination = self.root / folder

        # Canonicalize duplicate lessons: retain only the stronger evidence.
        for path in destination.glob("*.json"):
            try:
                existing = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if existing.get("lesson_key") != record["lesson_key"]:
                continue
            existing_quality = float(existing.get("quality_score", memory_quality(existing)))
            if existing_quality >= float(record["quality_score"]):
                return path
            path.unlink(missing_ok=True)

        digest = hashlib.sha256(
            json.dumps(record, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()[:16]
        path = destination / f"{grammar or 'unknown'}-{digest}.json"
        path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        self.prune(grammar=grammar)
        return path

    def _all_records(self, folder: str, grammar: str = "") -> list[tuple[Path, dict]]:
        records: list[tuple[Path, dict]] = []
        for path in (self.root / folder).glob("*.json"):
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if grammar and record.get("grammar") != grammar:
                continue
            record["quality_score"] = memory_quality(record)
            records.append((path, record))
        records.sort(
            key=lambda item: (float(item[1].get("quality_score", 0.0)), float(item[1].get("recorded_at", 0.0))),
            reverse=True,
        )
        return records

    def prune(self, *, grammar: str = "", max_per_bucket: int = 40, stale_days: int = 365) -> dict:
        """Retire weak/stale lessons and cap each grammar bucket."""
        removed = 0
        cutoff = time.time() - stale_days * 86400
        for folder in ("good-scenes", "bad-scenes"):
            records = self._all_records(folder, grammar)
            keep: list[tuple[Path, dict]] = []
            seen_keys: set[str] = set()
            for path, record in records:
                key = str(record.get("lesson_key") or _lesson_key(
                    str(record.get("grammar", "")), str(record.get("visual_goal", "")),
                    list(record.get("problems", [])), list(record.get("revision", [])),
                ))
                quality = float(record.get("quality_score", memory_quality(record)))
                stale_and_weak = float(record.get("recorded_at", 0.0) or 0.0) < cutoff and quality < 0.45
                duplicate = key in seen_keys
                over_cap = len(keep) >= max_per_bucket
                if stale_and_weak or duplicate or over_cap:
                    path.unlink(missing_ok=True)
                    removed += 1
                    continue
                seen_keys.add(key)
                keep.append((path, record))
        return {"removed": removed}

    def _records(self, folder: str, grammar: str, limit: int) -> list[dict]:
        return [record for _, record in self._all_records(folder, grammar)[:limit]]

    def guidance(self, grammar: str, *, limit: int = 2, max_chars: int = 3500) -> str:
        rules = json.loads((self.root / "style-rules.json").read_text(encoding="utf-8"))
        good = self._records("good-scenes", grammar, limit)
        bad = self._records("bad-scenes", grammar, limit)
        lines = [
            "# 可复用风格记忆",
            "",
            f"> {MEMORY_SCHEMA_VERSION}：仅提供按质量排序的抽象经验，不包含历史 scene 的完整布局、源码、Prompt 或对话历史。",
            "",
            "## 固定规则",
        ]
        lines.extend(f"- 避免：{_clip(value, 180)}" for value in rules.get("avoid", [])[:8])
        lines.extend(f"- 优先：{_clip(value, 180)}" for value in rules.get("prefer", [])[:8])
        if good:
            lines.extend(["", f"## {grammar} 的高质量有效经验"])
            for item in good:
                lines.append(
                    f"- [q={float(item.get('quality_score', memory_quality(item))):.2f}] "
                    f"{_clip(item.get('visual_goal', ''), 220)}"
                )
        if bad:
            lines.extend(["", f"## {grammar} 的高价值失败经验"])
            for item in bad:
                details = "；".join(item.get("problems", []) + item.get("revision", []))
                lines.append(
                    f"- [q={float(item.get('quality_score', memory_quality(item))):.2f}] "
                    f"{_clip(details or item.get('visual_goal', ''), 300)}"
                )
        text = "\n".join(lines).strip() + "\n"
        return _clip(text, max_chars).rstrip() + "\n"

    def stats(self) -> dict:
        good = self._all_records("good-scenes")
        bad = self._all_records("bad-scenes")
        values = [float(record.get("quality_score", memory_quality(record))) for _, record in good + bad]
        return {
            "schema_version": MEMORY_SCHEMA_VERSION,
            "good_scenes": len(good),
            "bad_scenes": len(bad),
            "average_quality": round(sum(values) / len(values), 4) if values else 0.0,
        }


def memory_root(value: str, config_source: Path | None = None) -> Path:
    if value:
        candidate = Path(value).expanduser()
        if not candidate.is_absolute() and config_source is not None:
            candidate = config_source.parent / candidate
        return candidate.resolve()
    return (Path.home() / ".codex-harness-vibe" / "memory").resolve()
