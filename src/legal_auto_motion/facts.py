from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path


NUMERIC_FACT = re.compile(
    r"(?<!\d)(\d[\d,]*(?:\.\d+)?)\s*(万元|亿元|元|块|天|年|次|%|％|毫升|日)"
)
DATE = re.compile(r"(?<!\d)(?:19|20)\d{2}(?:[年./-]\d{1,2})?(?:[月./-]\d{1,2})?日?")
CASE_NUMBER = re.compile(r"[（(]?\d{4}[）)]?[^'\"<>]{0,20}(?:民|刑|行|赔|执|申|终|初|再)[^'\"<>]{0,16}\d+号?")
CJK_OR_DIGIT = re.compile(r"[\u3400-\u9fff0-9]")
CJK = re.compile(r"[\u3400-\u9fff]")


@dataclass(frozen=True)
class Violation:
    file: str
    visible_text: str
    reason: str


def normalize(value: str) -> str:
    return re.sub(r"[\s，,。；;：:、·]", "", value).replace("块", "元").replace("％", "%")


def date_key(value: str) -> tuple[int, ...]:
    return tuple(int(part) for part in re.findall(r"\d+", value))


def visible_copy_candidates(source: Path) -> list[str]:
    text = source.read_text(encoding="utf-8")
    decoded = re.sub(
        r"\\u\{([0-9a-fA-F]{1,6})\}|\\u([0-9a-fA-F]{4})",
        lambda match: chr(int(match.group(1) or match.group(2), 16)),
        text,
    )
    decoded = re.sub(r"/\*.*?\*/|//[^\r\n]*", "", decoded, flags=re.DOTALL)
    decoded = re.sub(r"\b(?:aria-label|title)\s*=\s*(['\"]).*?\1", "", decoded, flags=re.DOTALL)
    found: list[str] = []
    for match in re.finditer(r">([^<>{}]*[\u3400-\u9fff0-9][^<>{}]*)<", decoded):
        value = re.sub(r"\s+", " ", match.group(1)).strip()
        if value:
            found.append(value)
    for match in re.finditer(r"(['\"])([^'\"\r\n]*[\u3400-\u9fff][^'\"\r\n]*)\1", decoded):
        value = re.sub(r"\s+", " ", match.group(2)).strip()
        if value:
            found.append(value)
    return list(dict.fromkeys(found))


def numeric_facts(text: str) -> set[tuple[float, str]]:
    result: set[tuple[float, str]] = set()
    for match in NUMERIC_FACT.finditer(text):
        unit = match.group(2).replace("块", "元").replace("％", "%")
        result.add((float(match.group(1).replace(",", "")), unit))
    return result


def _copy_supported(visible: str, sources: list[str]) -> bool:
    candidate = normalize(visible)
    if not candidate:
        return True
    return any(candidate in normalize(source) or normalize(source) in candidate for source in sources)


def audit_sources(scene_dir: Path, contract: dict) -> list[Violation]:
    narration = str(contract.get("narration", ""))
    approved = [str(value) for value in contract.get("approved_copy", [])]
    sources = [narration, *approved]
    supported_numbers = numeric_facts(" ".join(sources))
    supported_dates = {date_key(value) for source in sources for value in DATE.findall(source)}
    violations: list[Violation] = []
    authored = [
        path
        for folder in (scene_dir / "scenes", scene_dir / "remotion")
        if folder.exists()
        for path in folder.rglob("*")
        if path.suffix.lower() in {".tsx", ".jsx", ".ts", ".js"}
    ]
    for source in authored:
        for visible in visible_copy_candidates(source):
            if CJK.search(visible) and not _copy_supported(visible, sources):
                violations.append(Violation(source.name, visible, "屏幕中文不在字幕或导演批准文案中"))
            for value, unit in numeric_facts(visible):
                exact = (value, unit) in supported_numbers
                derived = unit in {"天", "次"} and any(
                    source_unit == unit and 0 <= value <= source_value
                    for source_value, source_unit in supported_numbers
                )
                if not exact and not derived:
                    violations.append(Violation(source.name, visible, f"数值 {value:g}{unit} 无事实来源"))
            for date in DATE.findall(visible):
                if date_key(date) not in supported_dates:
                    violations.append(Violation(source.name, visible, f"日期 {date} 无事实来源"))
            if CASE_NUMBER.search(visible) and not any(CASE_NUMBER.search(item) for item in sources):
                violations.append(Violation(source.name, visible, "案号未经事实源支持"))
    unique = {(item.file, item.visible_text, item.reason): item for item in violations}
    return list(unique.values())


def write_audit(scene_dir: Path, contract: dict) -> dict:
    violations = audit_sources(scene_dir, contract)
    report = {
        "scene_id": contract.get("scene_id", scene_dir.name),
        "status": "rejected" if violations else "accepted",
        "approved_copy": contract.get("approved_copy", []),
        "violations": [asdict(item) for item in violations],
    }
    artifacts = scene_dir / "artifacts"
    artifacts.mkdir(exist_ok=True)
    (artifacts / "fact-audit.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    if violations:
        revision = {
            "instruction": "只使用 approved_copy 或字幕原文中的短语；删除所有无来源数字、日期、比例、案号和裁判文字。",
            **report,
        }
        (artifacts / "fact-revision-request.json").write_text(
            json.dumps(revision, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    return report
