from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path


FRAME_KEY = re.compile(
    r"\b((?:enter|entry|start|exit|end)|[A-Za-z_$][\w$]*(?:In|On|Drop|Impact|Done|Start|End|Exit))\s*:\s*(\d+)",
)


@dataclass(frozen=True)
class TimingViolation:
    file: str
    key: str
    frame: int
    duration_in_frames: int
    reason: str


def audit_timing(scene_dir: Path) -> list[TimingViolation]:
    metadata = json.loads((scene_dir / "scene-metadata.json").read_text(encoding="utf-8"))
    duration = int(metadata["duration_in_frames"])
    violations: list[TimingViolation] = []
    for source in (scene_dir / "scenes").rglob("*.tsx"):
        text = source.read_text(encoding="utf-8")
        for match in FRAME_KEY.finditer(text):
            key, frame = match.group(1), int(match.group(2))
            if frame >= duration:
                violations.append(
                    TimingViolation(
                        source.name,
                        key,
                        frame,
                        duration,
                        "动画使用了超出本镜头长度的帧；useCurrentFrame() 必须从局部0帧开始",
                    )
                )
    return violations


def write_timing_audit(scene_dir: Path) -> dict:
    violations = audit_timing(scene_dir)
    report = {
        "scene_id": scene_dir.name,
        "status": "rejected" if violations else "accepted",
        "violations": [asdict(item) for item in violations],
    }
    artifacts = scene_dir / "artifacts"
    artifacts.mkdir(exist_ok=True)
    (artifacts / "timing-audit.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    if violations:
        (artifacts / "timing-revision-request.json").write_text(
            json.dumps(
                {
                    "instruction": "把所有动画节拍改为本场景局部帧0..duration_in_frames-1；不要使用SRT全局帧。",
                    **report,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    return report
