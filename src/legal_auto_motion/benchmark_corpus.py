from __future__ import annotations

import json
from pathlib import Path

from .srt import parse_srt


ALLOWED_GRAMMARS = {
    "object_demo",
    "relationship_diagram",
    "timeline",
    "process_flow",
    "comparison",
    "document_evidence",
    "number_event",
    "interface_simulation",
    "kinetic_phrase",
    "visual_rest",
}


def validate_corpus(root: Path) -> dict:
    root = root.resolve()
    manifest_path = root / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    cases = manifest.get("cases", [])
    if not isinstance(cases, list) or len(cases) < 5:
        raise ValueError("benchmark corpus requires at least five cases")

    ids: set[str] = set()
    semantic_types: set[str] = set()
    rows: list[dict] = []
    for case in cases:
        case_id = str(case.get("id", "")).strip()
        if not case_id or case_id in ids:
            raise ValueError(f"duplicate or empty benchmark id: {case_id!r}")
        ids.add(case_id)
        semantic_type = str(case.get("semantic_type", "")).strip()
        if not semantic_type:
            raise ValueError(f"{case_id}: semantic_type is required")
        semantic_types.add(semantic_type)

        grammars = case.get("expected_grammars", [])
        if not grammars or any(grammar not in ALLOWED_GRAMMARS for grammar in grammars):
            raise ValueError(f"{case_id}: invalid expected_grammars")
        srt_path = root / str(case.get("srt", ""))
        if not srt_path.exists():
            raise FileNotFoundError(srt_path)
        cues = parse_srt(srt_path)
        if not cues:
            raise ValueError(f"{case_id}: SRT has no cues")
        if any(cue.end <= cue.start for cue in cues):
            raise ValueError(f"{case_id}: SRT contains invalid timing")
        rows.append(
            {
                "id": case_id,
                "semantic_type": semantic_type,
                "cue_count": len(cues),
                "duration_seconds": round(cues[-1].end - cues[0].start, 3),
                "expected_grammars": grammars,
            }
        )

    if len(semantic_types) < 5:
        raise ValueError("benchmark corpus must cover at least five semantic types")
    return {
        "version": str(manifest.get("version", "unknown")),
        "status": "valid",
        "case_count": len(rows),
        "semantic_type_count": len(semantic_types),
        "cases": rows,
    }
