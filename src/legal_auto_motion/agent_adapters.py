from __future__ import annotations

import hashlib
import json
import os
import shutil
import time
from dataclasses import dataclass
from pathlib import Path

from .config import ModelRoute
from .context_policy import CONTEXT_POLICY_VERSION
from .providers import claude_command, codex_text_command, codex_worker_command


DEFAULT_MAX_SCENE_PROMPT_CHARS = 18000


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


def _is_scene_worker_cwd(cwd: Path) -> bool:
    return cwd.name.startswith("scene-") and cwd.parent.name == "scenes"


def _isolation_prefix() -> str:
    return (
        f"# Context Isolation ({CONTEXT_POLICY_VERSION})\n"
        "This invocation is a fresh, single-scene worker context. Do not continue or reconstruct any prior scene session.\n"
        "Work only on the current scene directory. Never read sibling scene prompts, frame.md files, source code, artifacts, worker logs, or conversation history.\n"
        "Cross-scene consistency may use only the compact boundary_context in fact-contract.json and bounded artifacts/style-memory-guidance.md.\n"
        "Style memory is abstract guidance only: never copy a historical scene layout or code wholesale.\n"
        "Do not spawn subagents or create a persistent session. A retry is a new independent invocation.\n\n"
    )


def _write_invocation_manifest(artifacts: Path, cwd: Path, route: ModelRoute, prompt: str) -> None:
    payload = {
        "version": CONTEXT_POLICY_VERSION,
        "scene_id": cwd.name,
        "fresh_context": True,
        "provider": route.provider,
        "model": route.model,
        "prompt_chars": len(prompt),
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "created_at": time.time(),
        "session_history_inherited": False,
        "sibling_scene_history_allowed": False,
    }
    (artifacts / "invocation-context.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def build_invocation(
    cwd: Path,
    prompt: str,
    route: ModelRoute,
    *,
    structured: bool = False,
    schema_path: Path | None = None,
    max_prompt_chars: int = DEFAULT_MAX_SCENE_PROMPT_CHARS,
) -> AgentInvocation:
    cwd = cwd.resolve()
    artifacts = cwd / ".harness"
    artifacts.mkdir(parents=True, exist_ok=True)
    response_path = artifacts / "last-response.txt"
    response_path.unlink(missing_ok=True)
    env = os.environ.copy()

    effective_prompt = prompt
    if _is_scene_worker_cwd(cwd):
        effective_prompt = _isolation_prefix() + prompt
        if len(effective_prompt) > max_prompt_chars:
            raise ValueError(
                f"Scene worker prompt exceeds isolated context budget: {len(effective_prompt)} > {max_prompt_chars} chars"
            )
        env["HARNESS_CONTEXT_POLICY"] = CONTEXT_POLICY_VERSION
        env["HARNESS_SCENE_ID"] = cwd.name
        env["HARNESS_FRESH_CONTEXT"] = "1"
        _write_invocation_manifest(artifacts, cwd, route, effective_prompt)

    if route.provider == "claude":
        command = claude_command(_claude_executable(), route, structured=structured)
        if structured and schema_path is not None:
            command.extend(["--json-schema", schema_path.read_text(encoding="utf-8")])
        if route.model:
            env["CLAUDE_CODE_SUBAGENT_MODEL"] = route.model
        return AgentInvocation(command, effective_prompt, env, response_path=None)

    if route.provider == "codex_text":
        return AgentInvocation(codex_text_command(route, response_path, schema_path), effective_prompt, env, response_path)

    if route.provider == "codex_worker":
        return AgentInvocation(codex_worker_command(route, response_path), effective_prompt, env, response_path)

    if route.provider == "generic_cli":
        if not route.command:
            raise ValueError("generic_cli provider requires models.<role>.command")
        if _is_scene_worker_cwd(cwd) and "{prompt_file}" not in " ".join(route.command):
            raise ValueError("generic_cli scene workers must consume the per-invocation {prompt_file}")
        prompt_path = artifacts / "agent-prompt.txt"
        prompt_path.write_text(effective_prompt, encoding="utf-8")
        values = {
            "cwd": str(cwd),
            "model": route.model,
            "prompt_file": str(prompt_path),
            "response_file": str(response_path),
            "schema_file": str(schema_path or ""),
        }
        return AgentInvocation(_expand_command(route.command, values), None, env, response_path, prompt_path)

    raise ValueError(f"Unsupported text provider: {route.provider}")
