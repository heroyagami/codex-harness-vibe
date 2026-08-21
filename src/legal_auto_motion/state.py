from __future__ import annotations

import hashlib
import json
import time
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


NODE_ORDER = (
    "initialized", "directed", "prepared", "authored", "fact_passed",
    "timing_passed", "rendered", "visual_passed", "critic_passed",
    "transition_ready", "assembled",
)
_STATE_LOCK = threading.Lock()


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def input_hash(paths: Iterable[Path], values: Iterable[str] = ()) -> str:
    digest = hashlib.sha256()
    for path in sorted((Path(item) for item in paths), key=lambda item: str(item)):
        digest.update(str(path.name).encode("utf-8"))
        digest.update(file_hash(path).encode("ascii") if path.exists() else b"MISSING")
    for value in values:
        digest.update(str(value).encode("utf-8"))
    return digest.hexdigest()


@dataclass
class StateGraph:
    path: Path

    def load(self) -> dict:
        if not self.path.exists():
            return {"version": 1, "nodes": {}, "usage": {"calls": 0, "cost_usd": 0.0}}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def save(self, state: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.replace(self.path)

    def complete(self, node: str, fingerprint: str, *, outputs: Iterable[Path] = (), metadata: dict | None = None) -> None:
        if node not in NODE_ORDER:
            raise ValueError(f"Unknown state node: {node}")
        state = self.load()
        state["nodes"][node] = {
            "status": "complete", "input_hash": fingerprint, "completed_at": time.time(),
            "outputs": {str(path): file_hash(path) for path in outputs if path.exists()},
            "metadata": metadata or {},
        }
        self.save(state)

    def is_current(self, node: str, fingerprint: str) -> bool:
        record = self.load()["nodes"].get(node, {})
        if record.get("status") != "complete" or record.get("input_hash") != fingerprint:
            return False
        return all(Path(path).exists() and file_hash(Path(path)) == digest for path, digest in record.get("outputs", {}).items())

    def invalidate_from(self, node: str) -> list[str]:
        start = NODE_ORDER.index(node)
        state = self.load()
        removed = []
        for name in NODE_ORDER[start:]:
            if name in state["nodes"]:
                removed.append(name)
                del state["nodes"][name]
        self.save(state)
        return removed

    def reserve_call(self, *, max_calls: int = 0, max_cost_usd: float = 0.0, estimated_cost_usd: float = 0.0) -> None:
        with _STATE_LOCK:
            state = self.load()
            usage = state.setdefault("usage", {"calls": 0, "cost_usd": 0.0})
            if max_calls and usage["calls"] + 1 > max_calls:
                raise RuntimeError("Model-call budget exhausted")
            if max_cost_usd and usage["cost_usd"] + estimated_cost_usd > max_cost_usd:
                raise RuntimeError("Cost budget exhausted")
            usage["calls"] += 1
            usage["cost_usd"] = round(float(usage["cost_usd"]) + estimated_cost_usd, 6)
            self.save(state)
