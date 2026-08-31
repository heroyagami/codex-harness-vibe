from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path


def _events(run_dir: Path) -> list[dict]:
    events: list[dict] = []
    seen: set[str] = set()
    for path in sorted(run_dir.rglob("*state.json")):
        try:
            state = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        for event in state.get("usage", {}).get("events", []):
            call_id = str(event.get("call_id", ""))
            if call_id and call_id not in seen:
                seen.add(call_id)
                events.append(event | {"state_file": str(path.relative_to(run_dir))})
    return events


def build_production_report(run_dir: Path) -> dict:
    events = _events(run_dir)
    by_role: dict[str, dict] = defaultdict(lambda: {
        "calls": 0, "failed_calls": 0, "duration_seconds": 0.0, "estimated_cost_usd": 0.0,
    })
    failures: dict[str, int] = defaultdict(int)
    for event in events:
        role = str(event.get("role") or "unknown")
        item = by_role[role]
        item["calls"] += 1
        item["duration_seconds"] += float(event.get("duration_seconds", 0.0))
        item["estimated_cost_usd"] += float(event.get("actual_cost_usd", event.get("estimated_cost_usd", 0.0)))
        if event.get("status") not in {"complete", "succeeded"}:
            item["failed_calls"] += 1
            failures[str(event.get("error_category") or event.get("status") or "unknown")] += 1
    normalized_roles = {
        role: {
            **values,
            "duration_seconds": round(values["duration_seconds"], 3),
            "estimated_cost_usd": round(values["estimated_cost_usd"], 6),
        }
        for role, values in sorted(by_role.items())
    }
    report = {
        "summary": {
            "calls": len(events),
            "failed_calls": sum(1 for event in events if event.get("status") not in {"complete", "succeeded"}),
            "duration_seconds": round(sum(float(event.get("duration_seconds", 0.0)) for event in events), 3),
            "estimated_cost_usd": round(sum(float(event.get("actual_cost_usd", event.get("estimated_cost_usd", 0.0))) for event in events), 6),
        },
        "by_role": normalized_roles,
        "failure_categories": dict(sorted(failures.items())),
        "calls": events,
    }
    reports = run_dir / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    (reports / "production-metrics.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    lines = [
        "# Production metrics", "",
        f"- Calls: {report['summary']['calls']}",
        f"- Failed calls: {report['summary']['failed_calls']}",
        f"- Agent time: {report['summary']['duration_seconds']} seconds",
        f"- Estimated cost: ${report['summary']['estimated_cost_usd']:.6f}", "",
        "| Role | Calls | Failed | Seconds | Estimated cost |", "|---|---:|---:|---:|---:|",
    ]
    for role, item in normalized_roles.items():
        lines.append(
            f"| {role} | {item['calls']} | {item['failed_calls']} | {item['duration_seconds']} | ${item['estimated_cost_usd']:.6f} |"
        )
    (reports / "production-metrics.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report
