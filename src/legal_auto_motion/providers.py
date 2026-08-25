from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from .config import ModelRoute


class ProviderUnavailable(RuntimeError):
    pass


def claude_command(executable: str, route: ModelRoute, *, structured: bool = False) -> list[str]:
    command = [
        executable, "-p", "--safe-mode", "--no-session-persistence",
        "--dangerously-skip-permissions", "--output-format", "json" if structured else "text",
        "--disallowedTools", "Agent",
        "--append-system-prompt",
        (
            "Complete this task directly in the current session. Do not spawn "
            "Explore, Plan, or any other subagent. Never repeat an identical "
            "tool call with identical arguments; inspect the result and change "
            "approach if a command does not make progress."
        ),
    ]
    if route.model:
        command.extend(["--model", route.model])
    return command


def codex_command(route: ModelRoute, schema_path: Path, response_path: Path, images: list[Path]) -> list[str]:
    shim = shutil.which("codex.cmd")
    if shim:
        script = Path(shim).parent / "node_modules" / "@openai" / "codex" / "bin" / "codex.js"
        prefix = [shutil.which("node.exe") or shutil.which("node") or "node", str(script)]
    else:
        prefix = [shutil.which("codex") or "codex"]
    command = prefix + [
        "exec", "--skip-git-repo-check", "--ephemeral", "--ignore-rules", "--sandbox", "read-only",
        "--output-schema", str(schema_path), "--output-last-message", str(response_path),
    ]
    if route.model:
        command.extend(["--model", route.model])
    for image in images:
        command.extend(["--image", str(image)])
    command.append("-")
    return command


def codex_text_command(route: ModelRoute, response_path: Path, schema_path: Path | None = None) -> list[str]:
    shim = shutil.which("codex.cmd")
    if shim:
        script = Path(shim).parent / "node_modules" / "@openai" / "codex" / "bin" / "codex.js"
        prefix = [shutil.which("node.exe") or shutil.which("node") or "node", str(script)]
    else:
        prefix = [shutil.which("codex") or "codex"]
    command = prefix + [
        "exec", "--skip-git-repo-check", "--ephemeral", "--ignore-rules",
        "--sandbox", "read-only", "--output-last-message", str(response_path),
    ]
    if schema_path is not None:
        command.extend(["--output-schema", str(schema_path)])
    if route.model:
        command.extend(["--model", route.model])
    command.append("-")
    return command


def read_manual_critique(scene_dir: Path) -> dict:
    path = scene_dir / "artifacts" / "manual-critique.json"
    if not path.exists():
        raise ProviderUnavailable(f"Manual critic requires {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def is_retryable_model_failure(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in ("429", "quota", "usage limit", "rate limit", "overloaded", "timeout"))
