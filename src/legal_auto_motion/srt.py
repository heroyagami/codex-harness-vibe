from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Cue:
    index: int
    start: float
    end: float
    text: str
    timing: str

    @property
    def block(self) -> str:
        return f"{self.timing}\n{self.text}"


_TIMING = re.compile(
    r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*"
    r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})"
)


def _seconds(groups: tuple[str, ...]) -> float:
    h, m, s, ms = (int(value) for value in groups)
    return h * 3600 + m * 60 + s + ms / 1000


def parse_srt(path: Path) -> list[Cue]:
    raw = path.read_text(encoding="utf-8-sig").replace("\r\n", "\n").strip()
    cues: list[Cue] = []
    for block in re.split(r"\n{2,}", raw):
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if len(lines) < 3 or not lines[0].isdigit():
            continue
        match = _TIMING.fullmatch(lines[1])
        if not match:
            raise ValueError(f"Invalid SRT timing: {lines[1]}")
        start = _seconds(match.groups()[:4])
        end = _seconds(match.groups()[4:])
        if end <= start:
            raise ValueError(f"Cue {lines[0]} has non-positive duration")
        cues.append(Cue(int(lines[0]), start, end, " ".join(lines[2:]), lines[1]))
    if not cues:
        raise ValueError(f"No valid cues found in {path}")
    for previous, current in zip(cues, cues[1:]):
        if current.start < previous.end - 0.001:
            raise ValueError(f"Overlapping cues: {previous.index} and {current.index}")
    return cues

