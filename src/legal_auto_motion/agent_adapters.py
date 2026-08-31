from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from .config import ModelRoute
from .providers import claude_command, codex_text_command, codex_worker_command


@dataclass(frozen=True)
class AgentInvocation:
    command: list[str]
    stdin: str | None
    env: dict[str, str]
    response_path: Path | None = None
    prompt_path: Path | None = None


def _claude_executable() -> str:
    npm_shim = shutil.which("claude.cmd")
    if npm_shim:
        native = Path(npm_shim).parent / "node_modules" / "@anthropic-ai" / "claude-code" / "bin" / "claude.exe"
        if native.exists():
            return str(native)
    return shutil.which("claude.exe") or shutil.which("claude") or "claude"


def _expand_command(command: tuple[str, ...], values: dict[str, str]) -> list[str]:
    result = []
    for argument in command:
        try:
            result.append(argument.format_map(values))
        except KeyError as exc:
            raise ValueError(f"Unsupported generic_cli placeholder: {exc.args[0]}") from exc
    return result


def build_invocation(
    cwd: Path,
    prompt: str,
    route: ModelRoute,
    *,
    structured: bool = False,
    schema_path: Path | None = None,
) -> AgentInvocation:
    cwd = cwd.resolve()
    artifacts = cwd / ".harness"
    artifacts.mkdir(parents=True, exist_ok=True)
    response_path = artifacts / "last-response.txt"
    response_path.unlink(missing_ok=True)
    env = os.environ.copy()

    if route.provider == "claude":
        command = claude_command(_claude_executable(), route, structured=structured)
        if structured and schema_path is not None:
            command.extend(["--json-schema", schema_path.read_text(encoding="utf-8")])
        if route.model:
            env["CLAUDE_CODE_SUBAGENT_MODEL"] = route.model
        return AgentInvocation(command, prompt, env, response_path=None)

    if route.provider == "codex_text":
        return AgentInvocation(codex_text_command(route, response_path, schema_path), prompt, env, response_path)

    if route.provider == "codex_worker":
        return AgentInvocation(codex_worker_command(route, response_path), prompt, env, response_path)

    if route.provider == "generic_cli":
        if not route.command:
            raise ValueError("generic_cli provider requires models.<role>.command")
        prompt_path = artifacts / "agent-prompt.txt"
        prompt_path.write_text(prompt, encoding="utf-8")
        values = {
            "cwd": str(cwd),
            "model": route.model,
            "prompt_file": str(prompt_path),
            "response_file": str(response_path),
            "schema_file": str(schema_path or ""),
        }
        return AgentInvocation(_expand_command(route.command, values), None, env, response_path, prompt_path)

    raise ValueError(f"Unsupported text provider: {route.provider}")
